from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from harnessiq.agents import (
    AgentModelRequest,
    AgentModelResponse,
    AgentParameterSection,
    AgentRuntimeConfig,
    BaseAgent,
)
from harnessiq.shared.tools import CONTEXT_SELECT_CHECKPOINT, RegisteredTool, ToolCall, ToolDefinition
from harnessiq.tools import HookResponse, ToolResult, define_hook_tool
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
        runtime_config: AgentRuntimeConfig | None = None,
        repo_root: str | Path | None = None,
    ) -> None:
        super().__init__(
            name="inspectable_agent",
            model=model,
            tool_executor=tool_executor,
            runtime_config=runtime_config or AgentRuntimeConfig(include_default_output_sink=False),
            repo_root=repo_root,
        )

    def build_instance_payload(self) -> dict[str, Any]:
        return {}

    def build_system_prompt(self) -> str:
        return "System prompt"

    def load_parameter_sections(self) -> list[AgentParameterSection]:
        return [AgentParameterSection(title="State", content="initial")]


def _constant_tool(tool_key: str, name: str, handler) -> RegisteredTool:
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


@pytest.fixture(autouse=True)
def _disable_langsmith_client() -> None:
    with patch("harnessiq.agents.base.agent.build_langsmith_client", return_value=None):
        yield


def test_before_run_hook_can_pause_agent_execution() -> None:
    pause_hook = define_hook_tool(
        key="hooks.tests.pause_before_run",
        description="Pause immediately before the first model turn.",
        phases=("before_run",),
        handler=lambda context: HookResponse(
            pause_reason=f"{context.phase} approval required",
            pause_details={"phase": context.phase},
        ),
    )
    model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])
    agent = _InspectableAgent(
        model=model,
        tool_executor=ToolRegistry([]),
        runtime_config=AgentRuntimeConfig(
            hooks=(pause_hook,),
            include_default_output_sink=False,
        ),
    )

    result = agent.run(max_cycles=1)

    assert result.status == "paused"
    assert result.pause_reason == "before_run approval required"
    assert model.requests == []


def test_before_tool_hook_can_short_circuit_tool_execution() -> None:
    executed_calls: list[dict[str, object]] = []
    registry = ToolRegistry(
        [
            _constant_tool(
                "session.echo",
                "echo",
                lambda arguments: executed_calls.append(dict(arguments)) or {"echoed": arguments["text"]},
            )
        ]
    )
    model = _FakeModel(
        [
            AgentModelResponse(
                assistant_message="Use the echo tool.",
                tool_calls=(ToolCall(tool_key="session.echo", arguments={"text": "hello"}),),
                should_continue=False,
            )
        ]
    )
    short_circuit_hook = define_hook_tool(
        key="hooks.tests.short_circuit",
        description="Return a synthetic tool result before execution.",
        phases=("before_tool",),
        handler=lambda context: HookResponse(
            tool_result=ToolResult(
                tool_key=context.tool_key or "unknown.tool",
                output={"short_circuited": True, "arguments": context.tool_arguments},
            )
        ),
    )
    agent = _InspectableAgent(
        model=model,
        tool_executor=registry,
        runtime_config=AgentRuntimeConfig(
            hooks=(short_circuit_hook,),
            include_default_output_sink=False,
        ),
    )

    result = agent.run(max_cycles=1)

    assert result.status == "completed"
    assert executed_calls == []
    assert agent.transcript[-1].entry_type == "tool_result"
    assert agent.transcript[-1].output == {
        "short_circuited": True,
        "arguments": {"text": "hello"},
    }


def test_after_tool_hook_can_replace_tool_result() -> None:
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
                should_continue=False,
            )
        ]
    )
    override_hook = define_hook_tool(
        key="hooks.tests.override_after_tool",
        description="Replace one tool result after execution.",
        phases=("after_tool",),
        handler=lambda context: HookResponse(
            tool_result=ToolResult(
                tool_key=context.tool_key or "unknown.tool",
                output={"rewritten_output": context.tool_output},
            )
        ),
    )
    agent = _InspectableAgent(
        model=model,
        tool_executor=registry,
        runtime_config=AgentRuntimeConfig(
            hooks=(override_hook,),
            include_default_output_sink=False,
        ),
    )

    result = agent.run(max_cycles=1)

    assert result.status == "completed"
    assert agent.transcript[-1].output == {"rewritten_output": {"echoed": "hello"}}


def test_before_checkpoint_hook_receives_checkpoint_name_and_can_short_circuit() -> None:
    captured_checkpoint_names: list[str | None] = []
    executed_calls: list[dict[str, object]] = []
    model = _FakeModel(
        [
            AgentModelResponse(
                assistant_message="Save a checkpoint.",
                tool_calls=(
                    ToolCall(
                        tool_key=CONTEXT_SELECT_CHECKPOINT,
                        arguments={"checkpoint_name": "draft_state", "description": "Draft progress"},
                    ),
                ),
                should_continue=False,
            )
        ]
    )
    checkpoint_hook = define_hook_tool(
        key="hooks.tests.before_checkpoint",
        description="Capture checkpoint metadata before the checkpoint tool executes.",
        phases=("before_checkpoint",),
        handler=lambda context: captured_checkpoint_names.append(context.checkpoint_name)
        or HookResponse(
            tool_result=ToolResult(
                tool_key=context.tool_key or CONTEXT_SELECT_CHECKPOINT,
                output={"checkpoint_name": context.checkpoint_name, "phase": context.phase},
            )
        ),
    )
    agent = _InspectableAgent(
        model=model,
        tool_executor=ToolRegistry(
            [
                _constant_tool(
                    CONTEXT_SELECT_CHECKPOINT,
                    "checkpoint",
                    lambda arguments: executed_calls.append(dict(arguments)) or {"executed": True},
                )
            ]
        ),
        runtime_config=AgentRuntimeConfig(
            hooks=(checkpoint_hook,),
            include_default_output_sink=False,
        ),
    )

    result = agent.run(max_cycles=1)

    assert result.status == "completed"
    assert captured_checkpoint_names == ["draft_state"]
    assert executed_calls == []
    assert agent.transcript[-1].output == {
        "checkpoint_name": "draft_state",
        "phase": "before_checkpoint",
    }


def test_approval_policy_on_request_pauses_before_tool_execution() -> None:
    executed_calls: list[dict[str, object]] = []
    registry = ToolRegistry(
        [
            _constant_tool(
                "session.echo",
                "echo",
                lambda arguments: executed_calls.append(dict(arguments)) or {"echoed": arguments["text"]},
            )
        ]
    )
    model = _FakeModel(
        [
            AgentModelResponse(
                assistant_message="Use the echo tool.",
                tool_calls=(ToolCall(tool_key="session.echo", arguments={"text": "hello"}),),
                should_continue=False,
            )
        ]
    )
    agent = _InspectableAgent(
        model=model,
        tool_executor=registry,
        runtime_config=AgentRuntimeConfig(
            approval_policy="on-request",
            include_default_output_sink=False,
        ),
    )

    result = agent.run(max_cycles=1)

    assert result.status == "paused"
    assert result.pause_reason == "approval required"
    assert executed_calls == []


def test_allowed_tools_policy_blocks_disallowed_tool_calls() -> None:
    executed_calls: list[dict[str, object]] = []
    registry = ToolRegistry(
        [
            _constant_tool(
                "session.echo",
                "echo",
                lambda arguments: executed_calls.append(dict(arguments)) or {"echoed": arguments["text"]},
            )
        ]
    )
    model = _FakeModel(
        [
            AgentModelResponse(
                assistant_message="Use the echo tool.",
                tool_calls=(ToolCall(tool_key="session.echo", arguments={"text": "hello"}),),
                should_continue=False,
            )
        ]
    )
    agent = _InspectableAgent(
        model=model,
        tool_executor=registry,
        runtime_config=AgentRuntimeConfig(
            allowed_tools=("filesystem.*",),
            include_default_output_sink=False,
        ),
    )

    result = agent.run(max_cycles=1)

    assert result.status == "completed"
    assert executed_calls == []
    assert agent.transcript[-1].output == {
        "error": "Tool 'session.echo' is not allowed by the current allowed_tools policy.",
        "policy": {
            "allowed_tools": ["filesystem.*"],
            "approval_policy": "never",
        },
    }
