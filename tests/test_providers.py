"""Tests for provider request translation helpers."""

from __future__ import annotations

import asyncio
import unittest
from unittest import mock

from src.providers import ProviderFormatError, SUPPORTED_PROVIDERS, normalize_messages
from src.providers.anthropic.helpers import build_request as build_anthropic_request
from src.providers.gemini.helpers import build_request as build_gemini_request
from src.providers.grok.helpers import build_request as build_grok_request
from src.providers.langsmith import (
    trace_agent_run,
    trace_async_agent_run,
    trace_async_model_call,
    trace_async_tool_call,
    trace_model_call,
    trace_tool_call,
)
from src.providers.openai.helpers import build_request as build_openai_request
from src.tools import ECHO_TEXT, create_builtin_registry


class ProviderHelperTests(unittest.TestCase):
    def setUp(self) -> None:
        registry = create_builtin_registry()
        self.tools = registry.definitions([ECHO_TEXT])
        self.messages = [
            {"role": "user", "content": "ping"},
            {"role": "assistant", "content": "pong"},
        ]

    def test_supported_providers_are_stable(self) -> None:
        self.assertEqual(SUPPORTED_PROVIDERS, ("anthropic", "openai", "grok", "gemini"))

    def test_normalize_messages_rejects_unknown_roles(self) -> None:
        with self.assertRaises(ProviderFormatError):
            normalize_messages([{"role": "tool", "content": "nope"}])

    def test_normalize_messages_rejects_inline_system_when_disallowed(self) -> None:
        with self.assertRaises(ProviderFormatError):
            normalize_messages([{"role": "system", "content": "dup"}], allow_system=False)

    def test_anthropic_request_uses_system_and_input_schema(self) -> None:
        request = build_anthropic_request(
            model_name="claude-sonnet",
            system_prompt="Be precise.",
            messages=self.messages,
            tools=self.tools,
        )

        self.assertEqual(request["system"], "Be precise.")
        self.assertEqual(request["messages"], self.messages)
        self.assertEqual(request["tools"][0]["name"], "echo_text")
        self.assertIn("input_schema", request["tools"][0])

    def test_openai_request_prepends_system_message_and_function_tools(self) -> None:
        request = build_openai_request(
            model_name="gpt-4.1",
            system_prompt="Be precise.",
            messages=self.messages,
            tools=self.tools,
        )

        self.assertEqual(request["messages"][0], {"role": "system", "content": "Be precise."})
        self.assertEqual(request["tools"][0]["type"], "function")
        self.assertEqual(request["tools"][0]["function"]["name"], "echo_text")
        self.assertFalse(request["tools"][0]["function"]["strict"])

    def test_grok_request_uses_openai_style_translation(self) -> None:
        request = build_grok_request(
            model_name="grok-2",
            system_prompt="Be precise.",
            messages=self.messages,
            tools=self.tools,
        )

        self.assertEqual(request["messages"][0]["role"], "system")
        self.assertEqual(request["tools"][0]["function"]["parameters"]["type"], "object")
        self.assertNotIn("strict", request["tools"][0]["function"])

    def test_gemini_request_uses_contents_and_function_declarations(self) -> None:
        request = build_gemini_request(
            model_name="gemini-2.0-flash",
            system_prompt="Be precise.",
            messages=self.messages,
            tools=self.tools,
        )

        self.assertEqual(request["system_instruction"], {"parts": [{"text": "Be precise."}]})
        self.assertEqual(request["contents"][0]["role"], "user")
        self.assertEqual(request["contents"][1]["role"], "model")
        self.assertEqual(request["tools"][0]["functionDeclarations"][0]["name"], "echo_text")


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
        )

        with mock.patch("src.providers.langsmith._get_langsmith_module", return_value=fake_langsmith):
            result = wrapped("hello")

        self.assertEqual(result, {"reply": "HELLO"})
        self.assertEqual(
            fake_langsmith.tracing_context_calls,
            [{"project_name": "Support Agents"}],
        )
        self.assertEqual(fake_langsmith.trace_calls[0]["name"], "support_agent.run")
        self.assertEqual(fake_langsmith.trace_calls[0]["run_type"], "chain")
        self.assertEqual(fake_langsmith.trace_calls[0]["tags"], ["support", "agent"])
        self.assertEqual(fake_langsmith.trace_calls[0]["metadata"], {"team": "support"})
        self.assertEqual(
            fake_langsmith.trace_calls[0]["inputs"],
            {"args": ["hello"], "kwargs": {}},
        )
        self.assertEqual(fake_langsmith.run_trees[0].end_calls[-1]["outputs"], {"output": {"reply": "HELLO"}})

    def test_trace_model_call_records_prompt_messages_tools_and_payload(self) -> None:
        fake_langsmith = _FakeLangSmith()
        request_payload = {
            "model": "gpt-4.1",
            "messages": list(self.messages),
        }

        with mock.patch("src.providers.langsmith._get_langsmith_module", return_value=fake_langsmith):
            result = trace_model_call(
                lambda: {"id": "resp_123"},
                provider="openai",
                model_name="gpt-4.1",
                system_prompt="Stay precise.",
                messages=self.messages,
                tools=self.tools,
                request_payload=request_payload,
                metadata={"agent": "support"},
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

        @trace_agent_run(name="decorated_agent.run", project_name="Decorated Agents")
        def run_agent(user_input: str) -> dict[str, str]:
            return {"reply": user_input}

        with mock.patch("src.providers.langsmith._get_langsmith_module", return_value=fake_langsmith):
            result = run_agent("hello")

        self.assertEqual(result, {"reply": "hello"})
        self.assertEqual(fake_langsmith.trace_calls[0]["name"], "decorated_agent.run")
        self.assertEqual(fake_langsmith.tracing_context_calls[0]["project_name"], "Decorated Agents")

    def test_trace_tool_call_records_tool_identity_and_result(self) -> None:
        fake_langsmith = _FakeLangSmith()

        with mock.patch("src.providers.langsmith._get_langsmith_module", return_value=fake_langsmith):
            result = trace_tool_call(
                lambda: {"text": "done"},
                tool_name="echo_text",
                tool_key=ECHO_TEXT,
                arguments={"text": "done"},
                project_name="Tool Project",
            )

        self.assertEqual(result, {"text": "done"})
        self.assertEqual(fake_langsmith.tracing_context_calls[0]["project_name"], "Tool Project")
        self.assertEqual(fake_langsmith.trace_calls[0]["run_type"], "tool")
        self.assertEqual(
            fake_langsmith.trace_calls[0]["inputs"],
            {"tool_name": "echo_text", "tool_key": ECHO_TEXT, "arguments": {"text": "done"}},
        )
        self.assertEqual(fake_langsmith.run_trees[0].end_calls[-1]["outputs"], {"result": {"text": "done"}})

    def test_trace_model_call_records_errors_before_reraising(self) -> None:
        fake_langsmith = _FakeLangSmith()

        def boom() -> dict[str, str]:
            message = "provider timed out"
            raise RuntimeError(message)

        with mock.patch("src.providers.langsmith._get_langsmith_module", return_value=fake_langsmith):
            with self.assertRaisesRegex(RuntimeError, "provider timed out"):
                trace_model_call(
                    boom,
                    provider="openai",
                    model_name="gpt-4.1",
                    system_prompt="Stay precise.",
                    messages=self.messages,
                )

        self.assertEqual(fake_langsmith.run_trees[0].end_calls[-1]["error"], "provider timed out")


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
        )

        with mock.patch("src.providers.langsmith._get_langsmith_module", return_value=fake_langsmith):
            result = asyncio.run(wrapped("trace"))

        self.assertEqual(result, {"reply": "ecart"})
        self.assertEqual(fake_langsmith.trace_calls[0]["name"], "run_agent")
        self.assertEqual(fake_langsmith.trace_calls[0]["run_type"], "chain")
        self.assertEqual(fake_langsmith.run_trees[0].end_calls[-1]["outputs"], {"output": {"reply": "ecart"}})

    def test_trace_async_model_and_tool_calls_support_async_operations(self) -> None:
        fake_langsmith = _FakeLangSmith()

        async def model_operation() -> dict[str, str]:
            return {"id": "async_response"}

        async def tool_operation() -> dict[str, str]:
            return {"status": "ok"}

        with mock.patch("src.providers.langsmith._get_langsmith_module", return_value=fake_langsmith):
            model_result = asyncio.run(
                trace_async_model_call(
                    model_operation,
                    provider="anthropic",
                    model_name="claude-sonnet",
                    system_prompt="Be concise.",
                    messages=[{"role": "user", "content": "ping"}],
                    tools=[],
                    name="anthropic.chat",
                )
            )
            tool_result = asyncio.run(
                trace_async_tool_call(
                    tool_operation,
                    tool_name="echo_text",
                    arguments={"text": "ping"},
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

        @trace_async_agent_run(name="decorated_async.run", project_name="Decorated Async Agents")
        async def run_agent(value: str) -> dict[str, str]:
            return {"reply": value}

        with mock.patch("src.providers.langsmith._get_langsmith_module", return_value=fake_langsmith):
            result = asyncio.run(run_agent("hello"))

        self.assertEqual(result, {"reply": "hello"})
        self.assertEqual(fake_langsmith.trace_calls[0]["name"], "decorated_async.run")
        self.assertEqual(fake_langsmith.tracing_context_calls[0]["project_name"], "Decorated Async Agents")


if __name__ == "__main__":
    unittest.main()
