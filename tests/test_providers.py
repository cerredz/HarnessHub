"""Tests for LangSmith provider tracing helpers."""

from __future__ import annotations

import asyncio
import unittest
from unittest import mock

from harnessiq.providers.langsmith import (
    trace_agent_run,
    trace_async_agent_run,
    trace_async_model_call,
    trace_async_tool_call,
    trace_model_call,
    trace_tool_call,
)
from harnessiq.shared.http import ProviderHTTPError
from harnessiq.shared.tools import ECHO_TEXT
from harnessiq.tools import create_builtin_registry


class _FakeRunTree:
    def __init__(self) -> None:
        self.end_calls: list[dict[str, object | None]] = []

    def end(
        self,
        *,
        outputs: dict[str, object] | None = None,
        error: str | None = None,
        end_time: object | None = None,
        events: object | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        self.end_calls.append(
            {
                "outputs": outputs,
                "error": error,
                "end_time": end_time,
                "events": events,
                "metadata": metadata,
            }
        )


class _FakeTraceContextManager:
    def __init__(self, run_tree: _FakeRunTree | None = None) -> None:
        self._run_tree = run_tree

    def __enter__(self) -> _FakeRunTree | None:
        return self._run_tree

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False

    async def __aenter__(self) -> _FakeRunTree | None:
        return self._run_tree

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False


class _FakeLangSmith:
    def __init__(self) -> None:
        self.trace_calls: list[dict[str, object | None]] = []
        self.tracing_context_calls: list[dict[str, object | None]] = []
        self.run_trees: list[_FakeRunTree] = []

    def tracing_context(self, **kwargs: object) -> _FakeTraceContextManager:
        self.tracing_context_calls.append(dict(kwargs))
        return _FakeTraceContextManager()

    def trace(self, name: str, run_type: str = "chain", **kwargs: object) -> _FakeTraceContextManager:
        self.trace_calls.append({"name": name, "run_type": run_type, **dict(kwargs)})
        run_tree = _FakeRunTree()
        self.run_trees.append(run_tree)
        return _FakeTraceContextManager(run_tree)


class LangSmithTracingTests(unittest.TestCase):
    def setUp(self) -> None:
        registry = create_builtin_registry()
        self.tools = registry.definitions([ECHO_TEXT])
        self.messages = [
            {"role": "user", "content": "Where is the harness?"},
            {"role": "assistant", "content": "Checking inventory."},
        ]

    def test_trace_agent_run_wraps_sync_function_with_chain_trace(self) -> None:
        fake_langsmith = _FakeLangSmith()

        def run_agent(user_input: str) -> dict[str, str]:
            return {"reply": user_input.upper()}

        wrapped = trace_agent_run(
            run_agent,
            name="support_agent.run",
            project_name="Support Agents",
            tags=["support", "agent"],
            metadata={"team": "support"},
            client=object(),
        )

        with mock.patch("harnessiq.providers.langsmith._get_langsmith_module", return_value=fake_langsmith):
            result = wrapped("hello")

        self.assertEqual(result, {"reply": "HELLO"})
        self.assertEqual(fake_langsmith.tracing_context_calls[0]["project_name"], "Support Agents")
        self.assertTrue(fake_langsmith.tracing_context_calls[0]["enabled"])
        self.assertIsNotNone(fake_langsmith.tracing_context_calls[0]["client"])
        self.assertEqual(fake_langsmith.trace_calls[0]["name"], "support_agent.run")
        self.assertEqual(fake_langsmith.trace_calls[0]["run_type"], "chain")
        self.assertEqual(fake_langsmith.trace_calls[0]["tags"], ["support", "agent"])
        self.assertEqual(fake_langsmith.trace_calls[0]["metadata"], {"team": "support"})
        self.assertEqual(fake_langsmith.trace_calls[0]["inputs"], {"args": ["hello"], "kwargs": {}})
        self.assertEqual(fake_langsmith.run_trees[0].end_calls[-1]["outputs"], {"output": {"reply": "HELLO"}})

    def test_trace_model_call_records_prompt_messages_tools_and_payload(self) -> None:
        fake_langsmith = _FakeLangSmith()
        request_payload = {
            "model": "gpt-4.1",
            "messages": list(self.messages),
        }

        with mock.patch("harnessiq.providers.langsmith._get_langsmith_module", return_value=fake_langsmith):
            result = trace_model_call(
                lambda: {"id": "resp_123"},
                provider="openai",
                model_name="gpt-4.1",
                system_prompt="Stay precise.",
                messages=self.messages,
                tools=self.tools,
                request_payload=request_payload,
                metadata={"agent": "support"},
                client=object(),
            )

        self.messages[0]["content"] = "mutated"
        request_payload["messages"][0]["content"] = "mutated"

        self.assertEqual(result, {"id": "resp_123"})
        self.assertEqual(fake_langsmith.trace_calls[0]["name"], "openai.model_call")
        self.assertEqual(fake_langsmith.trace_calls[0]["run_type"], "llm")
        captured_inputs = fake_langsmith.trace_calls[0]["inputs"]
        self.assertEqual(captured_inputs["provider"], "openai")
        self.assertEqual(captured_inputs["model_name"], "gpt-4.1")
        self.assertEqual(captured_inputs["system_prompt"], "Stay precise.")
        self.assertEqual(captured_inputs["messages"][0]["content"], "Where is the harness?")
        self.assertEqual(captured_inputs["tools"][0]["key"], ECHO_TEXT)
        self.assertEqual(captured_inputs["request_payload"]["messages"][0]["content"], "Where is the harness?")
        self.assertEqual(fake_langsmith.run_trees[0].end_calls[-1]["outputs"], {"response": {"id": "resp_123"}})

    def test_trace_agent_run_supports_decorator_configuration(self) -> None:
        fake_langsmith = _FakeLangSmith()

        @trace_agent_run(name="decorated_agent.run", project_name="Decorated Agents", client=object())
        def run_agent(user_input: str) -> dict[str, str]:
            return {"reply": user_input}

        with mock.patch("harnessiq.providers.langsmith._get_langsmith_module", return_value=fake_langsmith):
            result = run_agent("hello")

        self.assertEqual(result, {"reply": "hello"})
        self.assertEqual(fake_langsmith.trace_calls[0]["name"], "decorated_agent.run")
        self.assertEqual(fake_langsmith.tracing_context_calls[0]["project_name"], "Decorated Agents")
        self.assertTrue(fake_langsmith.tracing_context_calls[0]["enabled"])

    def test_trace_tool_call_records_tool_identity_and_result(self) -> None:
        fake_langsmith = _FakeLangSmith()

        with mock.patch("harnessiq.providers.langsmith._get_langsmith_module", return_value=fake_langsmith):
            result = trace_tool_call(
                lambda: {"text": "done"},
                tool_name="echo_text",
                tool_key=ECHO_TEXT,
                arguments={"text": "done"},
                project_name="Tool Project",
                client=object(),
            )

        self.assertEqual(result, {"text": "done"})
        self.assertEqual(fake_langsmith.tracing_context_calls[0]["project_name"], "Tool Project")
        self.assertTrue(fake_langsmith.tracing_context_calls[0]["enabled"])
        self.assertEqual(fake_langsmith.trace_calls[0]["run_type"], "tool")
        self.assertEqual(
            fake_langsmith.trace_calls[0]["inputs"],
            {"tool_name": "echo_text", "tool_key": ECHO_TEXT, "arguments": {"text": "done"}},
        )
        self.assertEqual(fake_langsmith.run_trees[0].end_calls[-1]["outputs"], {"result": {"text": "done"}})

    def test_trace_model_call_records_errors_before_reraising(self) -> None:
        fake_langsmith = _FakeLangSmith()

        def boom() -> dict[str, str]:
            raise RuntimeError("provider timed out")

        with mock.patch("harnessiq.providers.langsmith._get_langsmith_module", return_value=fake_langsmith):
            with self.assertRaisesRegex(RuntimeError, "provider timed out"):
                trace_model_call(
                    boom,
                    provider="openai",
                    model_name="gpt-4.1",
                    system_prompt="Stay precise.",
                    messages=self.messages,
                    client=object(),
                )

        self.assertEqual(fake_langsmith.run_trees[0].end_calls[-1]["error"], "provider timed out")

    def test_trace_model_call_preserves_provider_http_error(self) -> None:
        fake_langsmith = _FakeLangSmith()

        def boom() -> dict[str, str]:
            raise ProviderHTTPError(
                provider="grok",
                message="Forbidden",
                status_code=403,
                url="https://api.x.ai/v1/chat/completions",
                body={"error": {"message": "Forbidden"}},
            )

        with mock.patch("harnessiq.providers.langsmith._get_langsmith_module", return_value=fake_langsmith):
            with self.assertRaises(ProviderHTTPError) as raised:
                trace_model_call(
                    boom,
                    provider="grok",
                    model_name="grok-4-1-fast",
                    system_prompt="Stay precise.",
                    messages=self.messages,
                    client=object(),
                )

        self.assertEqual(raised.exception.provider, "grok")
        self.assertEqual(raised.exception.status_code, 403)
        self.assertEqual(str(raised.exception), "grok request failed (403): Forbidden")
        self.assertEqual(fake_langsmith.run_trees[0].end_calls[-1]["error"], "grok request failed (403): Forbidden")

    def test_tracing_helpers_fail_open_without_credentials(self) -> None:
        fake_langsmith = _FakeLangSmith()
        with mock.patch("harnessiq.providers.langsmith._get_langsmith_module", return_value=fake_langsmith):
            result = trace_tool_call(
                lambda: {"status": "ok"},
                tool_name="echo_text",
                tool_key=ECHO_TEXT,
                arguments={"text": "done"},
            )

        self.assertEqual(result, {"status": "ok"})
        self.assertEqual(fake_langsmith.tracing_context_calls, [])
        self.assertEqual(fake_langsmith.trace_calls, [])


class AsyncLangSmithTracingTests(unittest.TestCase):
    def test_trace_async_agent_run_wraps_async_function_with_chain_trace(self) -> None:
        fake_langsmith = _FakeLangSmith()

        async def run_agent(value: str) -> dict[str, str]:
            return {"reply": value[::-1]}

        wrapped = trace_async_agent_run(
            run_agent,
            project_name="Async Agents",
            tags=["async"],
            metadata={"mode": "async"},
            client=object(),
        )

        with mock.patch("harnessiq.providers.langsmith._get_langsmith_module", return_value=fake_langsmith):
            result = asyncio.run(wrapped("trace"))

        self.assertEqual(result, {"reply": "ecart"})
        self.assertEqual(fake_langsmith.trace_calls[0]["name"], "run_agent")
        self.assertEqual(fake_langsmith.trace_calls[0]["run_type"], "chain")
        self.assertTrue(fake_langsmith.tracing_context_calls[0]["enabled"])
        self.assertEqual(fake_langsmith.run_trees[0].end_calls[-1]["outputs"], {"output": {"reply": "ecart"}})

    def test_trace_async_model_and_tool_calls_support_async_operations(self) -> None:
        fake_langsmith = _FakeLangSmith()

        async def model_operation() -> dict[str, str]:
            return {"id": "async_response"}

        async def tool_operation() -> dict[str, str]:
            return {"status": "ok"}

        with mock.patch("harnessiq.providers.langsmith._get_langsmith_module", return_value=fake_langsmith):
            model_result = asyncio.run(
                trace_async_model_call(
                    model_operation,
                    provider="anthropic",
                    model_name="claude-sonnet",
                    system_prompt="Be concise.",
                    messages=[{"role": "user", "content": "ping"}],
                    tools=[],
                    name="anthropic.chat",
                    client=object(),
                )
            )
            tool_result = asyncio.run(
                trace_async_tool_call(
                    tool_operation,
                    tool_name="echo_text",
                    arguments={"text": "ping"},
                    client=object(),
                )
            )

        self.assertEqual(model_result, {"id": "async_response"})
        self.assertEqual(tool_result, {"status": "ok"})
        self.assertEqual(fake_langsmith.trace_calls[0]["name"], "anthropic.chat")
        self.assertEqual(fake_langsmith.trace_calls[0]["run_type"], "llm")
        self.assertEqual(fake_langsmith.run_trees[0].end_calls[-1]["outputs"], {"response": {"id": "async_response"}})
        self.assertEqual(fake_langsmith.trace_calls[1]["run_type"], "tool")
        self.assertEqual(fake_langsmith.run_trees[1].end_calls[-1]["outputs"], {"result": {"status": "ok"}})

    def test_trace_async_agent_run_supports_decorator_configuration(self) -> None:
        fake_langsmith = _FakeLangSmith()

        @trace_async_agent_run(name="decorated_async.run", project_name="Decorated Async Agents", client=object())
        async def run_agent(value: str) -> dict[str, str]:
            return {"reply": value}

        with mock.patch("harnessiq.providers.langsmith._get_langsmith_module", return_value=fake_langsmith):
            result = asyncio.run(run_agent("hello"))

        self.assertEqual(result, {"reply": "hello"})
        self.assertEqual(fake_langsmith.trace_calls[0]["name"], "decorated_async.run")
        self.assertEqual(fake_langsmith.tracing_context_calls[0]["project_name"], "Decorated Async Agents")
        self.assertTrue(fake_langsmith.tracing_context_calls[0]["enabled"])


if __name__ == "__main__":
    unittest.main()
