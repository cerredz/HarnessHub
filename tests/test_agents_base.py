"""Tests for the generic agent runtime."""

from __future__ import annotations

import unittest

from src.agents import (
    AgentModelRequest,
    AgentModelResponse,
    AgentParameterSection,
    AgentPauseSignal,
    AgentRuntimeConfig,
    BaseAgent,
)
from src.shared.tools import RegisteredTool, ToolCall, ToolDefinition
from src.tools.registry import ToolRegistry


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
    ) -> None:
        self._parameter_versions = parameter_versions or ["initial"]
        self._parameter_index = 0
        super().__init__(
            name="inspectable_agent",
            model=model,
            tool_executor=tool_executor,
            runtime_config=runtime_config,
        )

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
        self.assertEqual(model.requests[1].transcript[1].entry_type, "tool_call")
        self.assertEqual(model.requests[1].transcript[2].entry_type, "tool_result")
        self.assertIn("session.echo", model.requests[1].transcript[1].content)
        self.assertIn("hello", model.requests[1].transcript[2].content)

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


if __name__ == "__main__":
    unittest.main()
