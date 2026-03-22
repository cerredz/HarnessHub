"""Tests for the generic agent runtime."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harnessiq.agents import (
    AgentModelRequest,
    AgentModelResponse,
    AgentParameterSection,
    AgentPauseSignal,
    AgentRuntimeConfig,
    BaseAgent,
)
from harnessiq.shared.agents import DEFAULT_AGENT_MAX_TOKENS, DEFAULT_AGENT_RESET_THRESHOLD
from harnessiq.shared.tools import CONTROL_PAUSE_FOR_HUMAN, HEAVY_COMPACTION, RegisteredTool, ToolCall, ToolDefinition
from harnessiq.tools import create_context_compaction_tools, create_general_purpose_tools
from harnessiq.tools.registry import ToolRegistry


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
        runtime_config: AgentRuntimeConfig | None = None,
        payload: dict | None = None,
        repo_root: str | Path | None = None,
    ) -> None:
        self._parameter_versions = parameter_versions or ["initial"]
        self._parameter_index = 0
        self._payload = payload or {}
        super().__init__(
            name="inspectable_agent",
            model=model,
            tool_executor=tool_executor,
            runtime_config=runtime_config,
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


class BaseAgentTests(unittest.TestCase):
    def test_runtime_config_defaults_align_with_shared_constants(self) -> None:
        runtime_config = AgentRuntimeConfig()

        self.assertEqual(runtime_config.max_tokens, DEFAULT_AGENT_MAX_TOKENS)
        self.assertEqual(runtime_config.reset_threshold, DEFAULT_AGENT_RESET_THRESHOLD)

    def test_run_records_tool_results_and_passes_transcript_to_next_turn(self) -> None:
        registry = ToolRegistry(
            [
                _constant_tool("session.echo", "echo", lambda arguments: {"echoed": arguments["text"]}),
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
                (Path(temp_dir) / "memory" / "agents" / "inspectable_agent" / first.instance_id).resolve(),
            )

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


if __name__ == "__main__":
    unittest.main()
