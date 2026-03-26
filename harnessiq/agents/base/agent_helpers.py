"""Private helper methods and utilities for the base agent runtime."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Sequence
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harnessiq.providers import build_langsmith_client, trace_agent_run, trace_tool_call
from harnessiq.providers.output_sinks import extract_model_metadata
from harnessiq.shared.agents import (
    AgentContextDirective,
    AgentContextEntry,
    AgentContextRuntimeState,
    AgentModelRequest,
    AgentModelResponse,
    AgentParameterSection,
    AgentPauseSignal,
    AgentRunResult,
    AgentTranscriptEntry,
    DEFAULT_AGENT_CONTEXT_MEMORY_FIELD_RULES,
    json_parameter_section,
)
from harnessiq.shared.hooks import HookContext, HookPhase, RegisteredHook
from harnessiq.shared.tools import CONTEXT_SELECT_CHECKPOINT, ToolCall, ToolDefinition, ToolResult
from harnessiq.tools.context import BoundContextToolExecutor, create_context_tools
from harnessiq.tools.hooks import create_default_hook_tools
from harnessiq.utils.ledger import JSONLLedgerSink, LedgerEntry, new_run_id

logger = logging.getLogger("harnessiq.agents.base.agent")
_CONTEXT_STATE_FILENAME = "context_runtime_state.json"
_CONTEXT_MEMORY_SECTION_TITLE = "Context Memory"
_DIRECTIVE_PRIORITY_ORDER = {"critical": 0, "standard": 1, "advisory": 2}


class BaseAgentHelpersMixin:
    """Implementation detail mixin that keeps BaseAgent focused on public behavior."""

    def _bind_context_tools(self, tool_executor):
        """Wrap the tool executor with the generic context-tool family."""
        return BoundContextToolExecutor(
            delegate=tool_executor,
            context_tools=create_context_tools(
                get_context_window=self.build_context_window,
                get_runtime_state=lambda: self._context_runtime_state,
                save_runtime_state=self._save_context_runtime_state,
                refresh_parameters=self.refresh_parameters,
                get_reset_count=lambda: self._reset_count,
                get_cycle_index=lambda: self._cycle_index,
                get_system_prompt=self.build_system_prompt,
                run_model_subcall=self._run_context_model_subcall,
            ),
        )

    def _effective_system_prompt(self) -> str:
        """Append any active context directives to the base system prompt."""
        prompt = self.build_system_prompt()
        directives = self._active_context_directives()
        if not directives:
            return prompt
        lines = [
            "[CONTEXT DIRECTIVES]",
            *(
                f"- ({directive.priority.upper()}) {directive.directive}"
                for directive in directives
            ),
        ]
        return f"{prompt}\n\n" + "\n".join(lines)

    def _compose_parameter_sections(
        self,
        base_sections: Sequence[AgentParameterSection],
    ) -> tuple[AgentParameterSection, ...]:
        """Merge durable sections, overrides, and context memory into one block."""
        state = self._context_runtime_state
        injected_first: list[AgentParameterSection] = []
        injected_before_memory: list[AgentParameterSection] = []
        injected_last: list[AgentParameterSection] = []

        for section in state.injected_sections:
            rendered = AgentParameterSection(title=section.label, content=section.content)
            if section.position in {"first", "after_master_prompt"}:
                injected_first.append(rendered)
            elif section.position == "before_memory":
                injected_before_memory.append(rendered)
            else:
                injected_last.append(rendered)

        resolved_base: list[AgentParameterSection] = []
        for section in base_sections:
            resolved_base.append(
                AgentParameterSection(
                    title=section.title,
                    content=state.section_overrides.get(section.title, section.content),
                )
            )

        memory_sections: list[AgentParameterSection] = []
        memory_payload = self._build_context_memory_payload()
        if memory_payload is not None:
            memory_sections.append(json_parameter_section(_CONTEXT_MEMORY_SECTION_TITLE, memory_payload))

        return tuple(
            [
                *injected_first,
                *resolved_base,
                *injected_before_memory,
                *memory_sections,
                *injected_last,
            ]
        )

    def _build_context_memory_payload(self) -> dict[str, Any] | None:
        """Render the persisted context state into a parameter-friendly payload."""
        state = self._context_runtime_state
        payload: dict[str, Any] = {}
        if state.memory_fields:
            payload["memory_fields"] = deepcopy(state.memory_fields)
            payload["memory_field_rules"] = dict(state.memory_field_rules)
        directives = self._active_context_directives()
        if directives:
            payload["active_directives"] = [directive.as_dict() for directive in directives]
        if state.checkpoints:
            payload["checkpoints"] = [
                {
                    "checkpoint_name": checkpoint.checkpoint_name,
                    "description": checkpoint.description,
                    "key": checkpoint.key,
                    "saved_at_cycle": checkpoint.saved_at_cycle,
                    "saved_at_reset": checkpoint.saved_at_reset,
                    "token_count": checkpoint.token_count,
                }
                for checkpoint in state.checkpoints.values()
            ]
        return payload or None

    def _context_state_path(self) -> Path:
        """Return the file path used to persist generic context runtime state."""
        return self._memory_path / _CONTEXT_STATE_FILENAME

    def _load_context_runtime_state(self) -> AgentContextRuntimeState:
        """Load persisted context runtime state from disk when present."""
        path = self._context_state_path()
        if not path.exists():
            return AgentContextRuntimeState(
                memory_field_rules=dict(DEFAULT_AGENT_CONTEXT_MEMORY_FIELD_RULES)
            )
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return AgentContextRuntimeState(
                memory_field_rules=dict(DEFAULT_AGENT_CONTEXT_MEMORY_FIELD_RULES)
            )
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError(f"Expected JSON object in '{path.name}'.")
        return AgentContextRuntimeState.from_dict(payload)

    def _save_context_runtime_state(self) -> None:
        """Persist the current generic context runtime state to disk."""
        path = self._context_state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self._context_runtime_state.as_dict(), indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )

    def _active_context_directives(self) -> list[AgentContextDirective]:
        """Return active directives in the order they should be rendered."""
        return sorted(
            self._context_runtime_state.active_directives(self._reset_count),
            key=lambda directive: (
                _DIRECTIVE_PRIORITY_ORDER.get(directive.priority, 99),
                directive.directive_id,
            ),
        )

    def _expire_context_directives(self) -> None:
        """Drop expired directives and persist the reduced context state."""
        active = self._context_runtime_state.active_directives(self._reset_count)
        if len(active) == len(self._context_runtime_state.directives):
            return
        self._context_runtime_state.directives = active
        self._save_context_runtime_state()

    def _run_context_model_subcall(
        self,
        *,
        system_prompt: str,
        transcript_text: str,
        model_override: str | None = None,
    ) -> str:
        """Run a context-only model turn used by generic context tools."""
        model = self._model
        if model_override is not None:
            override_builder = getattr(model, "with_model_override", None)
            if callable(override_builder):
                model = override_builder(model_override)
        request = AgentModelRequest(
            agent_name=f"{self._name}.context_subcall",
            system_prompt=system_prompt,
            parameter_sections=(
                AgentParameterSection(title="Transcript", content=transcript_text),
            ),
            transcript=(),
            tools=(),
        )
        generate_turn_with_override = getattr(model, "generate_turn_with_override", None)
        if callable(generate_turn_with_override) and model_override is not None:
            response = generate_turn_with_override(request, model_override)
        else:
            response = model.generate_turn(request)
        summary = response.assistant_message.strip()
        if not summary:
            raise ValueError("Context summarization subcall returned empty assistant content.")
        return summary

    def _complete_run(
        self,
        result: AgentRunResult,
        *,
        started_at: datetime,
        total_estimated_request_tokens: int,
    ) -> AgentRunResult:
        """Emit final run bookkeeping and return the terminal result object."""
        self._emit_ledger_entry(
            started_at=started_at,
            finished_at=_utcnow(),
            status=result.status,
            cycles_completed=result.cycles_completed,
            total_estimated_request_tokens=total_estimated_request_tokens,
            pause_reason=result.pause_reason,
            error=None,
        )
        return result

    def _emit_ledger_entry(
        self,
        *,
        started_at: datetime,
        finished_at: datetime,
        status: str,
        cycles_completed: int,
        total_estimated_request_tokens: int,
        pause_reason: str | None,
        error: Exception | None,
    ) -> None:
        """Emit one ledger entry to every resolved output sink."""
        entry = LedgerEntry(
            run_id=self._last_run_id or new_run_id(),
            agent_name=self.name,
            started_at=started_at,
            finished_at=finished_at,
            status=status,  # type: ignore[arg-type]
            reset_count=self._reset_count,
            outputs=self.build_ledger_outputs(),
            tags=self.build_ledger_tags(),
            metadata=self._build_ledger_metadata(
                cycles_completed=cycles_completed,
                total_estimated_request_tokens=total_estimated_request_tokens,
                pause_reason=pause_reason,
                error=error,
            ),
        )
        for sink in self._resolved_output_sinks():
            try:
                sink.on_run_complete(entry)
            except Exception as sink_exc:  # pragma: no cover - sink failures are explicitly swallowed
                logger.warning("OutputSink %s failed: %s", type(sink).__name__, sink_exc)

    def _build_ledger_metadata(
        self,
        *,
        cycles_completed: int,
        total_estimated_request_tokens: int,
        pause_reason: str | None,
        error: Exception | None,
    ) -> dict[str, Any]:
        """Assemble framework metadata attached to the emitted ledger entry."""
        metadata: dict[str, Any] = {
            "approval_policy": self._runtime_config.approval_policy,
            "allowed_tools": list(self._runtime_config.allowed_tools),
            "cycles_completed": cycles_completed,
            "estimated_request_tokens": total_estimated_request_tokens,
            "hook_count": len(self.available_hooks()),
            "max_tokens": self._runtime_config.max_tokens,
            "memory_path": str(self._memory_path) if self._memory_path is not None else None,
            "reset_threshold": self._runtime_config.reset_threshold,
            "tool_count": len(self.available_tools()),
        }
        if pause_reason is not None:
            metadata["pause_reason"] = pause_reason
        if error is not None:
            metadata["error"] = {
                "message": str(error),
                "type": type(error).__name__,
            }
        metadata.update(extract_model_metadata(self._model))
        metadata.update(self.build_ledger_metadata())
        return metadata

    def _resolved_output_sinks(self) -> tuple[Any, ...]:
        """Resolve the default and explicit sinks for the current run."""
        sinks: list[Any] = []
        if self._runtime_config.include_default_output_sink:
            sinks.append(JSONLLedgerSink())
        sinks.extend(self._runtime_config.output_sinks)
        return tuple(sinks)

    def _resolved_hook_tools(self) -> tuple[RegisteredHook, ...]:
        """Return the pre-built ordered hook set for this runtime."""
        return self._hook_tools

    def _build_hook_tools(self) -> tuple[RegisteredHook, ...]:
        """Build runtime hooks from defaults plus any explicit config hooks."""
        hooks: list[RegisteredHook] = []
        if self._runtime_config.include_default_hooks:
            hooks.extend(
                create_default_hook_tools(
                    approval_policy=self._runtime_config.approval_policy,
                    allowed_tools=self._runtime_config.allowed_tools,
                )
            )
        hooks.extend(self._runtime_config.hooks)
        ordered = sorted(
            enumerate(hooks),
            key=lambda item: (item[1].definition.priority, item[0]),
        )
        return tuple(hook for _, hook in ordered)

    def _apply_before_run_hooks(self) -> AgentPauseSignal | None:
        """Run pre-run hooks and return a pause signal when one fires."""
        context = self._make_hook_context("before_run")
        _, _, pause_signal = self._run_hook_phase("before_run", context)
        return pause_signal

    def _trace_run(self, operation: Callable[[], Any]) -> Any:
        """Wrap one agent run in LangSmith tracing when enabled."""
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
        """Build the LangSmith client from runtime config when available."""
        return build_langsmith_client(
            api_key=self._runtime_config.langsmith_api_key,
            api_url=self._runtime_config.langsmith_api_url,
        )

    def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """Execute one tool call with tracing and normalized error handling."""
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
        """Look up the canonical tool definition for one tool key."""
        definitions = self._tool_executor.definitions([tool_key])
        if not definitions:
            return None
        return definitions[0]

    def _prepare_tool_call(
        self,
        tool_call: ToolCall,
    ) -> tuple[ToolCall | None, ToolResult | None, AgentPauseSignal | None]:
        """Run pre-tool hooks and return the executable tool call payload."""
        tool_definition = self._resolve_tool_definition(tool_call.tool_key)
        tool_name = tool_definition.name if tool_definition is not None else tool_call.tool_key
        context = self._make_hook_context(
            "before_tool",
            tool_key=tool_call.tool_key,
            tool_name=tool_name,
            tool_arguments=tool_call.arguments,
            checkpoint_name=self._checkpoint_name_for_tool_call(tool_call),
        )
        if self._is_checkpoint_tool_call(tool_call):
            checkpoint_context = self._make_hook_context(
                "before_checkpoint",
                tool_key=tool_call.tool_key,
                tool_name=tool_name,
                tool_arguments=context.tool_arguments,
                checkpoint_name=context.checkpoint_name,
            )
            checkpoint_context, override_result, pause_signal = self._run_hook_phase(
                "before_checkpoint",
                checkpoint_context,
            )
            if pause_signal is not None or override_result is not None:
                prepared_call = ToolCall(
                    tool_key=tool_call.tool_key,
                    arguments=checkpoint_context.tool_arguments or tool_call.arguments,
                )
                return prepared_call, override_result, pause_signal
            context = context.with_updates(tool_arguments=checkpoint_context.tool_arguments)
        context, override_result, pause_signal = self._run_hook_phase("before_tool", context)
        prepared_call = ToolCall(
            tool_key=tool_call.tool_key,
            arguments=context.tool_arguments or tool_call.arguments,
        )
        return prepared_call, override_result, pause_signal

    def _finalize_tool_result(
        self,
        tool_call: ToolCall,
        result: ToolResult,
    ) -> tuple[ToolResult, AgentPauseSignal | None]:
        """Run post-tool hooks and return the final recorded result."""
        tool_definition = self._resolve_tool_definition(result.tool_key)
        tool_name = tool_definition.name if tool_definition is not None else result.tool_key
        context = self._make_hook_context(
            "after_tool",
            tool_key=result.tool_key,
            tool_name=tool_name,
            tool_arguments=tool_call.arguments,
            tool_output=result.output,
            checkpoint_name=self._checkpoint_name_for_tool_call(tool_call),
        )
        _, override_result, pause_signal = self._run_hook_phase("after_tool", context)
        return (override_result or result), pause_signal

    def _run_hook_phase(
        self,
        phase: HookPhase,
        context: HookContext,
    ) -> tuple[HookContext, ToolResult | None, AgentPauseSignal | None]:
        """Execute matching hooks for one phase until one alters control flow."""
        current_context = context
        for hook in self._resolved_hook_tools():
            if not hook.applies_to(phase):
                continue
            response = hook.execute(current_context)
            if response is None:
                continue
            if response.pause_reason is not None:
                return current_context, None, AgentPauseSignal(
                    reason=response.pause_reason,
                    details=deepcopy(response.pause_details) if response.pause_details is not None else None,
                )
            if response.tool_result is not None:
                return current_context, response.tool_result, None
            if response.tool_arguments is not None:
                current_context = current_context.with_updates(tool_arguments=response.tool_arguments)
        return current_context, None, None

    def _make_hook_context(
        self,
        phase: HookPhase,
        *,
        tool_key: str | None = None,
        tool_name: str | None = None,
        tool_arguments: dict[str, Any] | None = None,
        tool_output: Any = None,
        checkpoint_name: str | None = None,
    ) -> HookContext:
        """Build the normalized hook context for one lifecycle event."""
        return HookContext(
            phase=phase,
            agent_name=self.name,
            run_id=self._last_run_id,
            cycle_index=self._cycle_index,
            reset_count=self._reset_count,
            memory_path=str(self._memory_path) if self._memory_path is not None else None,
            available_tool_keys=tuple(definition.key for definition in self.available_tools()),
            tool_key=tool_key,
            tool_name=tool_name,
            tool_arguments=deepcopy(tool_arguments) if tool_arguments is not None else None,
            tool_output=deepcopy(tool_output),
            checkpoint_name=checkpoint_name,
        )

    def _is_checkpoint_tool_call(self, tool_call: ToolCall) -> bool:
        """Return whether the requested tool call targets checkpoint persistence."""
        return tool_call.tool_key == CONTEXT_SELECT_CHECKPOINT

    def _checkpoint_name_for_tool_call(self, tool_call: ToolCall) -> str | None:
        """Extract the logical checkpoint name from a checkpoint tool call."""
        if not self._is_checkpoint_tool_call(tool_call):
            return None
        raw_name = tool_call.arguments.get("checkpoint_name")
        if raw_name is None:
            return None
        return str(raw_name)

    def _record_assistant_response(self, response: AgentModelResponse) -> None:
        """Append one assistant turn and its requested tool calls to the transcript."""
        parts: list[str] = []
        if response.assistant_message.strip():
            parts.append(response.assistant_message.strip())
        if response.pause_reason:
            parts.append(f"Pause requested: {response.pause_reason}")
        self._transcript.append(
            AgentTranscriptEntry(
                entry_type="assistant",
                content="\n".join(parts) if parts else "(no assistant content)",
                role="assistant",
            )
        )
        for tool_call in response.tool_calls:
            arguments = json.dumps(tool_call.arguments, sort_keys=True)
            self._transcript.append(
                AgentTranscriptEntry(
                    entry_type="tool_call",
                    content=f"{tool_call.tool_key}\n{arguments}",
                    tool_key=tool_call.tool_key,
                    arguments=dict(tool_call.arguments),
                )
            )

    def _record_tool_result(self, result: ToolResult) -> None:
        """Append one normalized tool result to the transcript."""
        rendered_output = json.dumps(result.output, indent=2, sort_keys=True, default=str)
        self._transcript.append(
            AgentTranscriptEntry(
                entry_type="tool_result",
                content=f"{result.tool_key}\n{rendered_output}",
                tool_key=result.tool_key,
                output=deepcopy(result.output),
            )
        )

    def _should_reset_context(self) -> bool:
        """Return whether the transcript should be fully reset for token pressure."""
        if not self._transcript:
            return False
        return self._is_reset_helpful(self._runtime_config.reset_token_limit)

    def _should_prune_context(self) -> bool:
        """Return whether deterministic or token-based pruning should run now."""
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
        """Estimate whether clearing transcript state meaningfully reduces tokens."""
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
        return reset_request.estimated_tokens() < self._runtime_config.max_tokens

    def _apply_compaction_result(self, result: ToolResult) -> bool:
        """Apply a compaction tool payload directly into the active context."""
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
        """Replace the active transcript and parameters from a context snapshot."""
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

    def _allow_auto_reset_after_tool_result(self, result: ToolResult) -> bool:
        """Return whether a tool result allows immediate pruning or reset checks."""
        del result
        return True

    def _context_entry_to_transcript_entry(self, entry: dict[str, Any]) -> AgentTranscriptEntry:
        """Convert one context-window entry back into the transcript model."""
        kind = entry.get("kind")
        content = str(entry.get("content", ""))
        metadata = deepcopy(entry.get("metadata")) if isinstance(entry.get("metadata"), dict) else None
        if kind in {"message", "assistant"}:
            role = str(entry.get("role", "assistant"))
            return AgentTranscriptEntry(
                entry_type="user" if role == "user" else "assistant",
                content=content,
                role="user" if role == "user" else "assistant",
                metadata=metadata,
            )
        if kind == "tool_call":
            arguments = entry.get("arguments")
            return AgentTranscriptEntry(
                entry_type="tool_call",
                content=content,
                tool_key=str(entry.get("tool_key")) if entry.get("tool_key") is not None else None,
                tool_call_id=str(entry.get("tool_call_id")) if entry.get("tool_call_id") is not None else None,
                arguments=dict(arguments) if isinstance(arguments, dict) else None,
                metadata=metadata,
            )
        if kind == "tool_result":
            return AgentTranscriptEntry(
                entry_type="tool_result",
                content=content,
                tool_key=str(entry.get("tool_key")) if entry.get("tool_key") is not None else None,
                tool_call_id=str(entry.get("tool_call_id")) if entry.get("tool_call_id") is not None else None,
                output=deepcopy(entry.get("output")),
                metadata=metadata,
            )
        if kind == "summary":
            return AgentTranscriptEntry(entry_type="summary", content=content, metadata=metadata)
        if kind == "context":
            return AgentTranscriptEntry(
                entry_type="context",
                content=content,
                label=str(entry.get("label", "Context")),
                metadata=metadata,
            )
        raise ValueError(f"Unsupported context entry kind '{kind}'.")

    def _transcript_entry_to_context_entry(self, entry: AgentTranscriptEntry) -> AgentContextEntry:
        """Convert one transcript entry into the normalized context-window shape."""
        if entry.entry_type in {"assistant", "user"}:
            payload: AgentContextEntry = {
                "kind": "assistant" if entry.entry_type == "assistant" else "message",
                "role": "assistant" if entry.entry_type == "assistant" else "user",
                "content": entry.content,
            }
            if entry.metadata:
                payload["metadata"] = deepcopy(entry.metadata)
            return payload
        if entry.entry_type == "tool_call":
            payload = {
                "kind": "tool_call",
                "content": entry.content,
            }
            if entry.tool_key is not None:
                payload["tool_key"] = entry.tool_key
            if entry.tool_call_id is not None:
                payload["tool_call_id"] = entry.tool_call_id
            if entry.arguments is not None:
                payload["arguments"] = deepcopy(entry.arguments)
            if entry.metadata:
                payload["metadata"] = deepcopy(entry.metadata)
            return payload
        if entry.entry_type == "summary":
            payload: AgentContextEntry = {"kind": "summary", "content": entry.content}
            if entry.metadata:
                payload["metadata"] = deepcopy(entry.metadata)
            return payload
        if entry.entry_type == "context":
            payload = {
                "kind": "context",
                "label": entry.label or "Context",
                "content": entry.content,
            }
            if entry.metadata:
                payload["metadata"] = deepcopy(entry.metadata)
            return payload
        payload = {"kind": "tool_result", "content": entry.content}
        if entry.tool_key is not None:
            payload["tool_key"] = entry.tool_key
        if entry.tool_call_id is not None:
            payload["tool_call_id"] = entry.tool_call_id
        if entry.output is not None:
            payload["output"] = deepcopy(entry.output)
        if entry.metadata:
            payload["metadata"] = deepcopy(entry.metadata)
        return payload


def _resolve_repo_root(repo_root: str | Path | None, memory_path: Path | None) -> Path:
    """Resolve the repository root from an explicit path or a memory directory."""
    if repo_root is not None:
        return Path(repo_root).expanduser().resolve()
    if memory_path is not None:
        resolved_memory_path = Path(memory_path).expanduser().resolve()
        for candidate in (resolved_memory_path, *resolved_memory_path.parents):
            if (candidate / ".git").exists():
                return candidate
    return Path.cwd().resolve()


def _utcnow() -> datetime:
    """Return the current UTC timestamp for runtime bookkeeping."""
    return datetime.now(timezone.utc)
