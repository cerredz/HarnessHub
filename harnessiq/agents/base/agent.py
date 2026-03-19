"""Reusable agent runtime abstractions and loop orchestration."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Sequence

from harnessiq.providers import build_langsmith_client, trace_agent_run, trace_tool_call
from harnessiq.shared.agents import (
    AgentContextEntry,
    AgentContextWindow,
    AgentModel,
    AgentModelRequest,
    AgentModelResponse,
    AgentParameterSection,
    AgentPauseSignal,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeConfig,
    AgentToolExecutor,
    AgentTranscriptEntry,
    estimate_text_tokens,
)
from harnessiq.shared.tools import HEAVY_COMPACTION, LOG_COMPACTION, REMOVE_TOOL_RESULTS, REMOVE_TOOLS
from harnessiq.shared.tools import ToolCall, ToolDefinition, ToolResult


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
        memory_path: Path | None = None,
    ) -> None:
        self._name = name
        self._model = model
        self._tool_executor = tool_executor
        self._runtime_config = runtime_config or AgentRuntimeConfig()
        self._memory_path = memory_path
        self._parameter_sections: tuple[AgentParameterSection, ...] = ()
        self._transcript: list[AgentTranscriptEntry] = []
        self._reset_count = 0
        self._last_prune_progress = 0

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

    @property
    def memory_path(self) -> Path | None:
        return self._memory_path

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

    def inspect_tools(self, tool_keys: Sequence[str] | None = None) -> tuple[dict[str, Any], ...]:
        """Return rich inspection metadata for all or selected tools."""
        inspector = getattr(self._tool_executor, "inspect", None)
        if callable(inspector):
            return tuple(inspector(tool_keys))
        definitions = self._tool_executor.definitions(tool_keys)
        return tuple(definition.inspect() for definition in definitions)

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

    def pruning_progress_value(self) -> int:
        """Return the generic progress counter used by deterministic pruning.

        Concrete agents can override this to map pruning to durable domain work
        such as saved searches, queued tasks, or processed records.
        """
        return len(self._transcript)

    def run(self, *, max_cycles: int | None = None) -> AgentRunResult:
        return self._trace_run(lambda: self._run_loop(max_cycles=max_cycles))

    def _run_loop(self, *, max_cycles: int | None = None) -> AgentRunResult:
        """Run the agent loop until it pauses, completes, or hits ``max_cycles``."""
        self.prepare()
        self._reset_count = 0
        self._transcript.clear()
        self.refresh_parameters()
        self._last_prune_progress = self.pruning_progress_value()

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

            if not response.should_continue:
                return AgentRunResult(
                    status="completed",
                    cycles_completed=cycles_completed,
                    resets=self._reset_count,
                )

            if self._should_prune_context():
                self.reset_context()
                self._last_prune_progress = self.pruning_progress_value()

            if self._should_reset_context():
                self.reset_context()
                self._last_prune_progress = self.pruning_progress_value()

        return AgentRunResult(
            status="max_cycles_reached",
            cycles_completed=cycles_completed,
            resets=self._reset_count,
        )

    def _trace_run(self, operation):
        wrapped = trace_agent_run(
            operation,
            name=f"{self.name}.run",
            project_name=self._runtime_config.langsmith_project,
            tags=["harnessiq", "agent", self.name],
            metadata={
                "agent_name": self.name,
                "memory_path": str(self._memory_path) if self._memory_path is not None else None,
                "tool_count": len(self.available_tools()),
            },
            client=self._langsmith_client(),
            enabled=self._runtime_config.langsmith_tracing_enabled,
        )
        return wrapped()

    def _langsmith_client(self) -> Any | None:
        return build_langsmith_client(
            api_key=self._runtime_config.langsmith_api_key,
            api_url=self._runtime_config.langsmith_api_url,
        )

    def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        try:
            tool_definition = self._resolve_tool_definition(tool_call.tool_key)
            tool_name = tool_definition.name if tool_definition is not None else tool_call.tool_key
            return trace_tool_call(
                lambda: self._tool_executor.execute(tool_call.tool_key, tool_call.arguments),
                tool_name=tool_name,
                tool_key=tool_call.tool_key,
                arguments=tool_call.arguments,
                name=f"{self.name}.{tool_name}",
                project_name=self._runtime_config.langsmith_project,
                tags=["harnessiq", "tool", self.name],
                metadata={
                    "agent_name": self.name,
                    "tool_key": tool_call.tool_key,
                },
                client=self._langsmith_client(),
                enabled=self._runtime_config.langsmith_tracing_enabled,
            )
        except Exception as exc:  # pragma: no cover - exercised via tests through public behavior
            return ToolResult(
                tool_key=tool_call.tool_key,
                output={"error": str(exc)},
            )

    def _resolve_tool_definition(self, tool_key: str) -> ToolDefinition | None:
        definitions = self._tool_executor.definitions([tool_key])
        if not definitions:
            return None
        return definitions[0]

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

        return self._is_reset_helpful(self._runtime_config.reset_token_limit)

    def _should_prune_context(self) -> bool:
        progress_interval = self._runtime_config.prune_progress_interval
        if progress_interval is not None:
            current_progress = self.pruning_progress_value()
            if current_progress - self._last_prune_progress >= progress_interval:
                return True

        prune_token_limit = self._runtime_config.prune_token_limit
        if prune_token_limit is not None and self._transcript:
            return self._is_reset_helpful(prune_token_limit)

        return False

    def _is_reset_helpful(self, token_limit: int) -> bool:
        request = self.build_model_request()
        if request.estimated_tokens() < token_limit:
            return False

        reset_request = AgentModelRequest(
            agent_name=request.agent_name,
            system_prompt=request.system_prompt,
            parameter_sections=request.parameter_sections,
            transcript=(),
            tools=request.tools,
        )
        return reset_request.estimated_tokens() < token_limit

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
