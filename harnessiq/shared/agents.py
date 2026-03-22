"""Shared agent constants, aliases, and runtime data models."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal, Protocol, Sequence, TypedDict

from harnessiq.shared.tools import ToolCall, ToolDefinition, ToolResult

DEFAULT_AGENT_MAX_TOKENS = 80_000
DEFAULT_AGENT_RESET_THRESHOLD = 0.9

AgentContextEntryKind = Literal["parameter", "message", "tool_call", "tool_result", "summary"]
AgentMessageRole = Literal["system", "user", "assistant"]
AgentTranscriptEntryType = Literal["assistant", "tool_call", "tool_result", "summary"]
AgentRunStatus = Literal["completed", "paused", "max_cycles_reached"]


class _AgentContextEntryRequired(TypedDict):
    kind: AgentContextEntryKind


class AgentContextEntry(_AgentContextEntryRequired, total=False):
    """A normalized agent context-window entry."""

    role: AgentMessageRole
    content: str
    label: str
    tool_key: str
    tool_call_id: str
    arguments: dict[str, Any]
    output: Any
    metadata: dict[str, Any]


AgentContextWindow = list[AgentContextEntry]


def estimate_text_tokens(text: str) -> int:
    """Estimate token usage without depending on a tokenizer library."""
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


@dataclass(frozen=True, slots=True)
class AgentRuntimeConfig:
    """Runtime controls for the generic agent loop."""

    max_tokens: int = DEFAULT_AGENT_MAX_TOKENS
    reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD
    output_sinks: tuple[Any, ...] = ()
    include_default_output_sink: bool = True

    def __post_init__(self) -> None:
        if self.max_tokens <= 0:
            message = "max_tokens must be greater than zero."
            raise ValueError(message)
        if not 0 < self.reset_threshold <= 1:
            message = "reset_threshold must be between 0 and 1."
            raise ValueError(message)

    @property
    def reset_token_limit(self) -> int:
        """Return the token estimate that should trigger a transcript reset."""
        return max(1, int(self.max_tokens * self.reset_threshold))


@dataclass(frozen=True, slots=True)
class AgentParameterSection:
    """A named durable parameter block injected into model context."""

    title: str
    content: str

    def render(self) -> str:
        return f"## {self.title}\n{self.content}".rstrip()


@dataclass(frozen=True, slots=True)
class AgentTranscriptEntry:
    """A single rolling transcript entry managed by the harness."""

    entry_type: AgentTranscriptEntryType
    content: str

    def render(self) -> str:
        if self.entry_type == "assistant":
            label = "[ASSISTANT TURN]"
        elif self.entry_type == "tool_call":
            label = "[TOOL CALL]"
        elif self.entry_type == "summary":
            label = "[SUMMARY]"
        else:
            label = "[TOOL RESULT]"
        return f"{label}\n{self.content}".rstrip()


@dataclass(frozen=True, slots=True)
class AgentModelRequest:
    """Normalized request handed to a provider-agnostic model adapter."""

    agent_name: str
    system_prompt: str
    parameter_sections: tuple[AgentParameterSection, ...]
    transcript: tuple[AgentTranscriptEntry, ...]
    tools: tuple[ToolDefinition, ...]

    def render_parameter_block(self) -> str:
        return "\n\n".join(section.render() for section in self.parameter_sections)

    def render_transcript(self) -> str:
        return "\n\n".join(entry.render() for entry in self.transcript)

    def estimated_tokens(self) -> int:
        """Estimate the full request size including tool metadata."""
        tool_payload = json.dumps([tool.as_dict() for tool in self.tools], sort_keys=True)
        segments = (
            self.system_prompt,
            self.render_parameter_block(),
            self.render_transcript(),
            tool_payload,
        )
        combined = "\n\n".join(segment for segment in segments if segment)
        return estimate_text_tokens(combined)


@dataclass(frozen=True, slots=True)
class AgentModelResponse:
    """A provider-independent model turn returned to the harness."""

    assistant_message: str
    tool_calls: tuple[ToolCall, ...] = ()
    should_continue: bool = True
    pause_reason: str | None = None


@dataclass(frozen=True, slots=True)
class AgentPauseSignal:
    """Structured signal returned by a tool when human intervention is required."""

    reason: str
    details: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class AgentRunResult:
    """Terminal outcome for one invocation of the agent loop."""

    status: AgentRunStatus
    cycles_completed: int
    resets: int
    pause_reason: str | None = None


class AgentModel(Protocol):
    """Provider-agnostic execution contract used by the base agent loop."""

    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        """Return the next assistant turn for the provided context."""


class AgentToolExecutor(Protocol):
    """Small execution surface shared by tool registries and custom executors."""

    def definitions(self, tool_keys: Sequence[str] | None = None) -> list[ToolDefinition]:
        """Return canonical tool definitions for all or selected tools."""

    def execute(self, tool_key: str, arguments: dict[str, Any]) -> ToolResult:
        """Execute a tool and return a normalized result."""


__all__ = [
    "AgentContextEntry",
    "AgentContextEntryKind",
    "AgentContextWindow",
    "AgentMessageRole",
    "AgentModel",
    "AgentModelRequest",
    "AgentModelResponse",
    "AgentParameterSection",
    "AgentPauseSignal",
    "AgentRunResult",
    "AgentRunStatus",
    "AgentRuntimeConfig",
    "AgentToolExecutor",
    "AgentTranscriptEntry",
    "AgentTranscriptEntryType",
    "DEFAULT_AGENT_MAX_TOKENS",
    "DEFAULT_AGENT_RESET_THRESHOLD",
    "estimate_text_tokens",
]
