"""Tests for the generic agent runtime."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from harnessiq.agents import (
    AgentModelRequest,
    AgentModelResponse,
    AgentParameterSection,
    AgentPauseSignal,
    AgentRuntimeConfig,
    AgentTranscriptEntry,
    BaseAgent,
    json_parameter_section,
)
from harnessiq.shared.agents import DEFAULT_AGENT_MAX_TOKENS, DEFAULT_AGENT_RESET_THRESHOLD
from harnessiq.shared.tools import (
    CONTEXT_INJECT_ASSISTANT_NOTE,
    CONTEXT_PARAM_INJECT_SECTION,
    CONTROL_PAUSE_FOR_HUMAN,
    HEAVY_COMPACTION,
    RegisteredTool,
    ToolCall,
    ToolDefinition,
)
from harnessiq.tools import create_context_compaction_tools, create_general_purpose_tools
from harnessiq.tools.registry import ToolRegistry
from harnessiq.utils import LedgerEntry, build_agent_instance_dirname

_LANGSMITH_CLIENT_PATCHER = patch("harnessiq.agents.base.agent.build_langsmith_client", return_value=None)


def setUpModule() -> None:
    _LANGSMITH_CLIENT_PATCHER.start()


def tearDownModule() -> None:
    _LANGSMITH_CLIENT_PATCHER.stop()


class _FakeModel:
    def __init__(self, responses: list[AgentModelResponse]) -> None:
        self._responses = list(responses)
        self.requests: list[AgentModelRequest] = []

    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        self.requests.append(request)
        return self._responses[len(self.requests) - 1]


class _InspectableAgent(BaseAgent):
    def __init__(
        self,
        *,
        model: _FakeModel,
        tool_executor: ToolRegistry,
        parameter_versions: list[str] | None = None,
        progress_step: int | None = None,
        runtime_config: AgentRuntimeConfig | None = None,
        payload: dict | None = None,
        repo_root: str | Path | None = None,
    ) -> None:
        self._parameter_versions = parameter_versions or ["initial"]
        self._parameter_index = 0
        self._payload = payload or {}
        self._progress_step = progress_step
        self._progress_value = 0
        super().__init__(
            name="inspectable_agent",
            model=model,
            tool_executor=tool_executor,
            runtime_config=runtime_config or AgentRuntimeConfig(include_default_output_sink=False),
            repo_root=repo_root,
        )

    def build_instance_payload(self) -> dict:
        return self._payload

    def build_system_prompt(self) -> str:
        return "System prompt"

    def load_parameter_sections(self) -> list[AgentParameterSection]:
        index = min(self._parameter_index, len(self._parameter_versions) - 1)
        self._parameter_index += 1
        return [AgentParameterSection(title="State", content=self._parameter_versions[index])]

    def build_ledger_outputs(self) -> dict[str, object]:
        return {"parameter_state": self.parameter_sections[0].content}

    def build_ledger_tags(self) -> list[str]:
        return ["inspectable"]

    def pruning_progress_value(self) -> int:
        if self._progress_step is None:
            return super().pruning_progress_value()
        value = self._progress_value
        self._progress_value += self._progress_step
        return value


class _CollectingSink:
    def __init__(self) -> None:
        self.entries: list[LedgerEntry] = []

    def on_run_complete(self, entry: LedgerEntry) -> None:
        self.entries.append(entry)


class _FailingSink:
    def on_run_complete(self, entry: LedgerEntry) -> None:
        del entry
        raise RuntimeError("sink failed")


def _constant_tool(tool_key: str, name: str, handler):
    return RegisteredTool(
        definition=ToolDefinition(
            key=tool_key,
            name=name,
            description=f"{name} tool",
            input_schema={
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": True,
            },
        ),
        handler=handler,
    )


def _echo_handler(arguments: dict[str, object]) -> dict[str, object]:
    return {"echoed": arguments["text"]}


class BaseAgentTests(unittest.TestCase):
    def test_runtime_config_defaults_align_with_shared_constants(self) -> None:
        runtime_config = AgentRuntimeConfig()

        self.assertEqual(runtime_config.max_tokens, DEFAULT_AGENT_MAX_TOKENS)
        self.assertEqual(runtime_config.reset_threshold, DEFAULT_AGENT_RESET_THRESHOLD)
        self.assertIsNone(runtime_config.prune_progress_interval)
        self.assertIsNone(runtime_config.prune_token_limit)

    def test_run_records_tool_results_and_passes_transcript_to_next_turn(self) -> None:
        registry = ToolRegistry(
            [
                _constant_tool("session.echo", "echo", _echo_handler),
            ]
        )
        model = _FakeModel(
            [
                AgentModelResponse(
                    assistant_message="Use the echo tool.",
                    tool_calls=(ToolCall(tool_key="session.echo", arguments={"text": "hello"}),),
                    should_continue=True,
                ),
                AgentModelResponse(
                    assistant_message="Finished.",
                    should_continue=False,
                ),
            ]
        )
        agent = _InspectableAgent(model=model, tool_executor=registry)

        result = agent.run(max_cycles=5)

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.cycles_completed, 2)
        self.assertEqual(len(model.requests), 2)
        self.assertEqual(model.requests[0].transcript, ())
        self.assertEqual(len(model.requests[1].transcript), 3)
        self.assertEqual(model.requests[1].transcript[0].entry_type, "assistant")
        self.assertEqual(model.requests[1].transcript[1].entry_type, "tool_call")
        self.assertEqual(model.requests[1].transcript[2].entry_type, "tool_result")
        self.assertIn("session.echo", model.requests[1].transcript[1].content)
        self.assertIn("hello", model.requests[1].transcript[2].content)

    def test_base_agent_resolves_stable_instance_metadata(self) -> None:
        registry = ToolRegistry([])
        model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])
        payload = {"segment": "platform", "max_tokens": 1024}

        with tempfile.TemporaryDirectory() as temp_dir:
            first = _InspectableAgent(
                model=model,
                tool_executor=registry,
                payload=payload,
                repo_root=temp_dir,
            )
            second = _InspectableAgent(
                model=model,
                tool_executor=registry,
                payload=dict(payload),
                repo_root=temp_dir,
            )

            self.assertEqual(first.instance_id, second.instance_id)
            self.assertEqual(first.instance_name, second.instance_name)
            self.assertEqual(first.instance_record.memory_path, second.instance_record.memory_path)
            self.assertEqual(
                first.memory_path.resolve(),
                (
                    Path(temp_dir)
                    / "memory"
                    / "agents"
                    / "inspectable_agent"
                    / build_agent_instance_dirname(first.instance_id)
                ).resolve(),
            )

    def test_run_wraps_agent_and_tool_execution_in_tracing_helpers(self) -> None:
        registry = ToolRegistry(
            [
                _constant_tool("session.echo", "echo", _echo_handler),
            ]
        )
        model = _FakeModel(
            [
                AgentModelResponse(
                    assistant_message="Use the echo tool.",
                    tool_calls=(ToolCall(tool_key="session.echo", arguments={"text": "hello"}),),
                    should_continue=True,
                ),
                AgentModelResponse(
                    assistant_message="Finished.",
                    should_continue=False,
                ),
            ]
        )
        agent = _InspectableAgent(
            model=model,
            tool_executor=registry,
            runtime_config=AgentRuntimeConfig(langsmith_api_key="ls_test_123"),
        )

        def _wrap_agent(operation, **kwargs):
            del kwargs
            return lambda: operation()

        def _wrap_tool(operation, **kwargs):
            del kwargs
            return operation()

        with (
            patch("harnessiq.agents.base.agent.build_langsmith_client", return_value=object()) as mock_client,
            patch("harnessiq.agents.base.agent.trace_agent_run", side_effect=_wrap_agent) as mock_trace_agent,
            patch("harnessiq.agents.base.agent.trace_tool_call", side_effect=_wrap_tool) as mock_trace_tool,
        ):
            result = agent.run(max_cycles=5)

        self.assertEqual(result.status, "completed")
        self.assertEqual(mock_client.call_count, 2)
        self.assertEqual(mock_trace_agent.call_count, 1)
        self.assertEqual(mock_trace_tool.call_count, 1)
        self.assertEqual(mock_trace_agent.call_args.kwargs["name"], "inspectable_agent.run")
        self.assertEqual(mock_trace_tool.call_args.kwargs["tool_key"], "session.echo")
        self.assertEqual(mock_trace_tool.call_args.kwargs["tool_name"], "echo")

    def test_run_pauses_when_a_tool_returns_pause_signal(self) -> None:
        registry = ToolRegistry(
            [
                _constant_tool(
                    "session.pause",
                    "pause",
                    lambda arguments: AgentPauseSignal(reason="captcha required"),
                ),
            ]
        )
        model = _FakeModel(
            [
                AgentModelResponse(
                    assistant_message="Pause for a CAPTCHA.",
                    tool_calls=(ToolCall(tool_key="session.pause", arguments={}),),
                    should_continue=True,
                ),
            ]
        )
        agent = _InspectableAgent(model=model, tool_executor=registry)

        result = agent.run(max_cycles=3)

        self.assertEqual(result.status, "paused")
        self.assertEqual(result.pause_reason, "captcha required")
        self.assertEqual(result.cycles_completed, 1)
        self.assertEqual(len(model.requests), 1)

    def test_run_pauses_when_builtin_pause_tool_is_invoked(self) -> None:
        registry = ToolRegistry(create_general_purpose_tools())
        model = _FakeModel(
            [
                AgentModelResponse(
                    assistant_message="Request approval before continuing.",
                    tool_calls=(
                        ToolCall(
                            tool_key=CONTROL_PAUSE_FOR_HUMAN,
                            arguments={"reason": "approval required", "details": {"step": "send outreach"}},
                        ),
                    ),
                    should_continue=True,
                ),
            ]
        )
        agent = _InspectableAgent(model=model, tool_executor=registry)

        result = agent.run(max_cycles=3)

        self.assertEqual(result.status, "paused")
        self.assertEqual(result.pause_reason, "approval required")
        self.assertEqual(len(model.requests), 1)
    def test_run_resets_context_and_refreshes_parameters_when_budget_is_exceeded(self) -> None:
        registry = ToolRegistry([])
        model = _FakeModel(
            [
                AgentModelResponse(
                    assistant_message="x" * 400,
                    should_continue=True,
                ),
                AgentModelResponse(
                    assistant_message="done",
                    should_continue=False,
                ),
            ]
        )
        agent = _InspectableAgent(
            model=model,
            tool_executor=registry,
            parameter_versions=["initial", "refreshed"],
            runtime_config=AgentRuntimeConfig(max_tokens=100, reset_threshold=0.5),
        )

        result = agent.run(max_cycles=3)

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.resets, 1)
        self.assertEqual(len(model.requests), 2)
        self.assertEqual(model.requests[1].transcript, ())
        self.assertEqual(model.requests[1].parameter_sections[0].content, "refreshed")

    def test_run_resets_context_when_prune_progress_interval_is_reached(self) -> None:
        registry = ToolRegistry([])
        model = _FakeModel(
            [
                AgentModelResponse(assistant_message="keep going", should_continue=True),
                AgentModelResponse(assistant_message="done", should_continue=False),
            ]
        )
        agent = _InspectableAgent(
            model=model,
            tool_executor=registry,
            parameter_versions=["initial", "refreshed"],
            progress_step=2,
            runtime_config=AgentRuntimeConfig(
                max_tokens=10_000,
                reset_threshold=0.95,
                prune_progress_interval=2,
            ),
        )

        result = agent.run(max_cycles=3)

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.resets, 1)
        self.assertEqual(len(model.requests), 2)
        self.assertEqual(model.requests[1].transcript, ())
        self.assertEqual(model.requests[1].parameter_sections[0].content, "refreshed")

    def test_run_resets_context_when_explicit_prune_token_limit_is_reached(self) -> None:
        registry = ToolRegistry([])
        model = _FakeModel(
            [
                AgentModelResponse(assistant_message="x" * 400, should_continue=True),
                AgentModelResponse(assistant_message="done", should_continue=False),
            ]
        )
        agent = _InspectableAgent(
            model=model,
            tool_executor=registry,
            parameter_versions=["initial", "refreshed"],
            runtime_config=AgentRuntimeConfig(
                max_tokens=10_000,
                reset_threshold=0.99,
                prune_token_limit=80,
            ),
        )

        result = agent.run(max_cycles=3)

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.resets, 1)
        self.assertEqual(len(model.requests), 2)
        self.assertEqual(model.requests[1].transcript, ())
        self.assertEqual(model.requests[1].parameter_sections[0].content, "refreshed")

    def test_compaction_tool_result_rewrites_agent_context_window(self) -> None:
        registry = ToolRegistry(create_context_compaction_tools())
        compactable_window = [
            {"kind": "parameter", "label": "State", "content": "initial"},
            {"kind": "message", "role": "assistant", "content": "Earlier turn"},
            {"kind": "tool_result", "content": "session.echo\n{\"echoed\": \"hello\"}"},
        ]
        model = _FakeModel(
            [
                AgentModelResponse(
                    assistant_message="Use heavy compaction.",
                    tool_calls=(ToolCall(tool_key=HEAVY_COMPACTION, arguments={"context_window": compactable_window}),),
                    should_continue=True,
                ),
                AgentModelResponse(
                    assistant_message="Finished.",
                    should_continue=False,
                ),
            ]
        )
        agent = _InspectableAgent(model=model, tool_executor=registry)

        result = agent.run(max_cycles=3)

        self.assertEqual(result.status, "completed")
        self.assertEqual(len(model.requests), 2)
        self.assertEqual(model.requests[1].transcript, ())
        self.assertEqual(model.requests[1].parameter_sections[0].content, "initial")

    def test_run_emits_ledger_entry_to_injected_sink(self) -> None:
        registry = ToolRegistry([])
        sink = _CollectingSink()
        agent = _InspectableAgent(
            model=_FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)]),
            tool_executor=registry,
            runtime_config=AgentRuntimeConfig(
                output_sinks=(sink,),
                include_default_output_sink=False,
            ),
        )

        result = agent.run(max_cycles=1)

        self.assertEqual(result.status, "completed")
        self.assertEqual(len(sink.entries), 1)
        self.assertEqual(sink.entries[0].agent_name, "inspectable_agent")
        self.assertEqual(sink.entries[0].outputs["parameter_state"], "initial")
        self.assertEqual(sink.entries[0].tags, ["inspectable"])

    def test_sink_failures_are_swallowed_and_later_sinks_still_run(self) -> None:
        registry = ToolRegistry([])
        good_sink = _CollectingSink()
        agent = _InspectableAgent(
            model=_FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)]),
            tool_executor=registry,
            runtime_config=AgentRuntimeConfig(
                output_sinks=(_FailingSink(), good_sink),
                include_default_output_sink=False,
            ),
        )

        with self.assertLogs("harnessiq.agents.base.agent", level="WARNING") as logs:
            result = agent.run(max_cycles=1)

        self.assertEqual(result.status, "completed")
        self.assertEqual(len(good_sink.entries), 1)
        self.assertIn("OutputSink _FailingSink failed", "\n".join(logs.output))

    def test_default_jsonl_sink_writes_to_harnessiq_home(self) -> None:
        registry = ToolRegistry([])
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict("os.environ", {"HARNESSIQ_HOME": temp_dir}):
                agent = _InspectableAgent(
                    model=_FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)]),
                    tool_executor=registry,
                    runtime_config=AgentRuntimeConfig(),
                )

                agent.run(max_cycles=1)

                ledger_path = Path(temp_dir, "runs.jsonl")
                self.assertTrue(ledger_path.exists())
                self.assertIn("inspectable_agent", ledger_path.read_text(encoding="utf-8"))
    def test_runtime_config_rejects_invalid_prune_values(self) -> None:
        with self.assertRaises(ValueError):
            AgentRuntimeConfig(prune_progress_interval=0)
        with self.assertRaises(ValueError):
            AgentRuntimeConfig(prune_token_limit=0)
    def test_inspect_tools_returns_rich_metadata_for_registered_tools(self) -> None:
        registry = ToolRegistry(
            [
                _constant_tool("session.echo", "echo", _echo_handler),
            ]
        )
        agent = _InspectableAgent(model=_FakeModel([]), tool_executor=registry)

        payload = agent.inspect_tools()

        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["key"], "session.echo")
        self.assertEqual(payload[0]["description"], "echo tool")
        self.assertEqual(payload[0]["parameters"], [])
        self.assertEqual(payload[0]["function"]["module"], __name__)
        self.assertEqual(payload[0]["function"]["qualname"], "_echo_handler")

    def test_build_context_window_includes_parameters_and_transcript_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = _InspectableAgent(
                model=_FakeModel([]),
                tool_executor=ToolRegistry([]),
                repo_root=temp_dir,
            )
            agent.refresh_parameters()
            agent._transcript.extend(
                [
                    AgentTranscriptEntry(entry_type="assistant", content="hello"),
                    AgentTranscriptEntry(entry_type="tool_result", content='session.echo\n{"echoed": "hello"}'),
                ]
            )

            context_window = agent.build_context_window()

            self.assertEqual(context_window[0]["kind"], "parameter")
            self.assertEqual(context_window[0]["label"], "State")
            self.assertEqual(context_window[1]["kind"], "assistant")
            self.assertEqual(context_window[2]["kind"], "tool_result")

    def test_enable_context_tools_applies_injection_result_without_recording_tool_result(self) -> None:
        registry = ToolRegistry([])
        model = _FakeModel(
            [
                AgentModelResponse(
                    assistant_message="Inject a reminder note.",
                    tool_calls=(
                        ToolCall(
                            tool_key=CONTEXT_INJECT_ASSISTANT_NOTE,
                            arguments={"content": "Focus on the active objective.", "note_type": "plan"},
                        ),
                    ),
                    should_continue=True,
                ),
                AgentModelResponse(
                    assistant_message="Finished.",
                    should_continue=False,
                ),
            ]
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = _InspectableAgent(model=model, tool_executor=registry, repo_root=temp_dir)
            agent.enable_context_tools()

            result = agent.run(max_cycles=3)

            self.assertEqual(result.status, "completed")
            self.assertEqual(len(model.requests), 2)
            transcript = model.requests[1].transcript
            self.assertEqual(len(transcript), 3)
            self.assertEqual(transcript[0].entry_type, "assistant")
            self.assertEqual(transcript[1].entry_type, "tool_call")
            self.assertEqual(transcript[2].entry_type, "assistant")
            self.assertIn("[PLAN]", transcript[2].content)

    def test_enable_context_tools_records_group4_results_and_refreshes_parameters(self) -> None:
        registry = ToolRegistry([])
        model = _FakeModel(
            [
                AgentModelResponse(
                    assistant_message="Inject a runtime section.",
                    tool_calls=(
                        ToolCall(
                            tool_key=CONTEXT_PARAM_INJECT_SECTION,
                            arguments={
                                "section_label": "Runtime Note",
                                "content": "This section was injected mid-run.",
                                "position": "last",
                            },
                        ),
                    ),
                    should_continue=True,
                ),
                AgentModelResponse(
                    assistant_message="Finished.",
                    should_continue=False,
                ),
            ]
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = _InspectableAgent(model=model, tool_executor=registry, repo_root=temp_dir)
            agent.enable_context_tools()

            result = agent.run(max_cycles=3)

            self.assertEqual(result.status, "completed")
            self.assertEqual(len(model.requests), 2)
            second_request = model.requests[1]
            self.assertEqual(second_request.parameter_sections[-1].title, "Runtime Note")
            self.assertEqual(second_request.parameter_sections[-1].content, "This section was injected mid-run.")
            self.assertEqual([entry.entry_type for entry in second_request.transcript], ["assistant", "tool_call", "tool_result"])

    def test_json_parameter_section_renders_sorted_json_content(self) -> None:
        section = json_parameter_section("State", {"b": 2, "a": 1})

        self.assertEqual(section.title, "State")
        self.assertEqual(section.content, '{\n  "a": 1,\n  "b": 2\n}')


if __name__ == "__main__":
    unittest.main()
