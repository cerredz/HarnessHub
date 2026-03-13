"""Reusable agent runtime abstractions and loop orchestration."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Literal, Protocol, Sequence

from src.shared.agents import AgentContextEntry, AgentContextWindow
from src.shared.tools import HEAVY_COMPACTION, LOG_COMPACTION, REMOVE_TOOL_RESULTS, REMOVE_TOOLS
from src.shared.tools import ToolCall, ToolDefinition, ToolResult


def estimate_text_tokens(text: str) -> int:
    """Estimate token usage without depending on a tokenizer library."""
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


@dataclass(frozen=True, slots=True)
class AgentRuntimeConfig:
    """Runtime controls for the generic agent loop."""

    max_tokens: int = 80_000
    reset_threshold: float = 0.9

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


TranscriptEntryType = Literal["assistant", "tool_call", "tool_result", "summary"]


@dataclass(frozen=True, slots=True)
class AgentTranscriptEntry:
    """A single rolling transcript entry managed by the harness."""

    entry_type: TranscriptEntryType
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


AgentRunStatus = Literal["completed", "paused", "max_cycles_reached"]


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


class BaseAgent(ABC):
    """Shared harness for long-running tool-using agents."""

    _COMPACTION_TOOL_KEYS = frozenset(
        {
            REMOVE_TOOL_RESULTS,
            REMOVE_TOOLS,
            HEAVY_COMPACTION,
            LOG_COMPACTION,
        }
    )

    def __init__(
        self,
        *,
        name: str,
        model: AgentModel,
        tool_executor: AgentToolExecutor,
        runtime_config: AgentRuntimeConfig | None = None,
    ) -> None:
        self._name = name
        self._model = model
        self._tool_executor = tool_executor
        self._runtime_config = runtime_config or AgentRuntimeConfig()
        self._parameter_sections: tuple[AgentParameterSection, ...] = ()
        self._transcript: list[AgentTranscriptEntry] = []
        self._reset_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def runtime_config(self) -> AgentRuntimeConfig:
        return self._runtime_config

    @property
    def tool_executor(self) -> AgentToolExecutor:
        return self._tool_executor

    @property
    def parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        return self._parameter_sections

    @property
    def transcript(self) -> tuple[AgentTranscriptEntry, ...]:
        return tuple(self._transcript)

    @property
    def reset_count(self) -> int:
        return self._reset_count

    def build_context_window(self) -> AgentContextWindow:
        """Return the current context window including parameters and transcript entries."""
        if not self._parameter_sections:
            self.refresh_parameters()
        context_window: AgentContextWindow = [
            {"kind": "parameter", "label": section.title, "content": section.content}
            for section in self._parameter_sections
        ]
        for entry in self._transcript:
            context_window.append(self._transcript_entry_to_context_entry(entry))
        return context_window

    @abstractmethod
    def build_system_prompt(self) -> str:
        """Return the agent's current system prompt."""

    @abstractmethod
    def load_parameter_sections(self) -> Sequence[AgentParameterSection]:
        """Load the durable parameter block injected into the model context."""

    def prepare(self) -> None:
        """Perform any one-time setup before the run loop starts."""

    def available_tools(self) -> tuple[ToolDefinition, ...]:
        return tuple(self._tool_executor.definitions())

    def refresh_parameters(self) -> tuple[AgentParameterSection, ...]:
        sections = tuple(self.load_parameter_sections())
        self._parameter_sections = sections
        return sections

    def reset_context(self) -> None:
        self._transcript.clear()
        self.refresh_parameters()
        self._reset_count += 1

    def build_model_request(self) -> AgentModelRequest:
        if not self._parameter_sections:
            self.refresh_parameters()
        return AgentModelRequest(
            agent_name=self._name,
            system_prompt=self.build_system_prompt(),
            parameter_sections=self._parameter_sections,
            transcript=tuple(self._transcript),
            tools=self.available_tools(),
        )

    def run(self, *, max_cycles: int | None = None) -> AgentRunResult:
        """Run the agent loop until it pauses, completes, or hits ``max_cycles``."""
        self.prepare()
        self._reset_count = 0
        self._transcript.clear()
        self.refresh_parameters()

        cycles_completed = 0
        while max_cycles is None or cycles_completed < max_cycles:
            request = self.build_model_request()
            response = self._model.generate_turn(request)
            cycles_completed += 1
            self._record_assistant_response(response)

            if response.pause_reason is not None:
                return AgentRunResult(
                    status="paused",
                    cycles_completed=cycles_completed,
                    resets=self._reset_count,
                    pause_reason=response.pause_reason,
                )

            pause_signal: AgentPauseSignal | None = None
            for tool_call in response.tool_calls:
                result = self._execute_tool(tool_call)
                if self._apply_compaction_result(result):
                    continue
                self._record_tool_result(result)
                if isinstance(result.output, AgentPauseSignal):
                    pause_signal = result.output
                    break

            if pause_signal is not None:
                return AgentRunResult(
                    status="paused",
                    cycles_completed=cycles_completed,
                    resets=self._reset_count,
                    pause_reason=pause_signal.reason,
                )

            if self._should_reset_context():
                self.reset_context()

            if not response.should_continue:
                return AgentRunResult(
                    status="completed",
                    cycles_completed=cycles_completed,
                    resets=self._reset_count,
                )

        return AgentRunResult(
            status="max_cycles_reached",
            cycles_completed=cycles_completed,
            resets=self._reset_count,
        )

    def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        try:
            return self._tool_executor.execute(tool_call.tool_key, tool_call.arguments)
        except Exception as exc:  # pragma: no cover - exercised via tests through public behavior
            return ToolResult(
                tool_key=tool_call.tool_key,
                output={"error": str(exc)},
            )

    def _record_assistant_response(self, response: AgentModelResponse) -> None:
        parts: list[str] = []
        if response.assistant_message.strip():
            parts.append(response.assistant_message.strip())
        if response.pause_reason:
            parts.append(f"Pause requested: {response.pause_reason}")
        self._transcript.append(
            AgentTranscriptEntry(
                entry_type="assistant",
                content="\n".join(parts) if parts else "(no assistant content)",
            )
        )
        for tool_call in response.tool_calls:
            arguments = json.dumps(tool_call.arguments, sort_keys=True)
            self._transcript.append(
                AgentTranscriptEntry(
                    entry_type="tool_call",
                    content=f"{tool_call.tool_key}\n{arguments}",
                )
            )

    def _record_tool_result(self, result: ToolResult) -> None:
        rendered_output = json.dumps(result.output, indent=2, sort_keys=True, default=str)
        content = f"{result.tool_key}\n{rendered_output}"
        self._transcript.append(AgentTranscriptEntry(entry_type="tool_result", content=content))

    def _should_reset_context(self) -> bool:
        if not self._transcript:
            return False

        request = self.build_model_request()
        if request.estimated_tokens() < self._runtime_config.reset_token_limit:
            return False

        reset_request = AgentModelRequest(
            agent_name=request.agent_name,
            system_prompt=request.system_prompt,
            parameter_sections=request.parameter_sections,
            transcript=(),
            tools=request.tools,
        )
        return reset_request.estimated_tokens() < self._runtime_config.reset_token_limit

    def _apply_compaction_result(self, result: ToolResult) -> bool:
        if result.tool_key not in self._COMPACTION_TOOL_KEYS:
            return False
        if not isinstance(result.output, dict):
            return False
        context_window = result.output.get("context_window")
        if not isinstance(context_window, list):
            return False
        self._apply_context_window(context_window)
        return True

    def _apply_context_window(self, context_window: list[dict[str, Any]]) -> None:
        parameter_sections: list[AgentParameterSection] = []
        transcript: list[AgentTranscriptEntry] = []
        for entry in context_window:
            kind = entry.get("kind")
            if kind == "parameter":
                parameter_sections.append(
                    AgentParameterSection(
                        title=str(entry.get("label", "Parameters")),
                        content=str(entry.get("content", "")),
                    )
                )
                continue
            transcript.append(self._context_entry_to_transcript_entry(entry))
        self._parameter_sections = tuple(parameter_sections)
        self._transcript = transcript

    def _context_entry_to_transcript_entry(self, entry: dict[str, Any]) -> AgentTranscriptEntry:
        kind = entry.get("kind")
        content = str(entry.get("content", ""))
        if kind == "message":
            return AgentTranscriptEntry(entry_type="assistant", content=content)
        if kind == "tool_call":
            return AgentTranscriptEntry(entry_type="tool_call", content=content)
        if kind == "tool_result":
            return AgentTranscriptEntry(entry_type="tool_result", content=content)
        if kind == "summary":
            return AgentTranscriptEntry(entry_type="summary", content=content)
        raise ValueError(f"Unsupported context entry kind '{kind}'.")

    def _transcript_entry_to_context_entry(self, entry: AgentTranscriptEntry) -> AgentContextEntry:
        if entry.entry_type == "assistant":
            return {"kind": "message", "role": "assistant", "content": entry.content}
        if entry.entry_type == "tool_call":
            return {"kind": "tool_call", "content": entry.content}
        if entry.entry_type == "summary":
            return {"kind": "summary", "content": entry.content}
        return {"kind": "tool_result", "content": entry.content}


__all__ = [
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
    "BaseAgent",
    "estimate_text_tokens",
]
