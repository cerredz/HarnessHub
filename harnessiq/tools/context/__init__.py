"""Context-window manipulation tool family."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from harnessiq.shared.agents import (
    AgentContextEntry,
    AgentContextRuntimeState,
    AgentContextWindow,
    estimate_text_tokens,
)
from harnessiq.shared.tools import (
    CONTEXT_COMPACTION_TOOL_KEYS,
    CONTEXT_INJECT_ASSISTANT_NOTE,
    CONTEXT_INJECT_CONTEXT_BLOCK,
    CONTEXT_INJECT_HANDOFF_BRIEF,
    CONTEXT_INJECT_PROGRESS_MARKER,
    CONTEXT_INJECT_REPLAY_MEMORY,
    CONTEXT_INJECT_SYNTHETIC_TOOL_RESULT,
    CONTEXT_INJECT_TASK_REMINDER,
    CONTEXT_INJECT_TOOL_CALL_PAIR,
    CONTEXT_PARAMETER_TOOL_KEYS,
    CONTEXT_PARAM_APPEND_MEMORY_FIELD,
    CONTEXT_PARAM_BULK_WRITE_MEMORY,
    CONTEXT_PARAM_CLEAR_MEMORY_FIELD,
    CONTEXT_PARAM_INJECT_DIRECTIVE,
    CONTEXT_PARAM_INJECT_SECTION,
    CONTEXT_PARAM_OVERWRITE_MEMORY_FIELD,
    CONTEXT_PARAM_UPDATE_SECTION,
    CONTEXT_PARAM_WRITE_ONCE_MEMORY_FIELD,
    CONTEXT_SELECTIVE_TOOL_KEYS,
    CONTEXT_SELECT_ANNOTATE_ENTRY,
    CONTEXT_SELECT_CHECKPOINT,
    CONTEXT_SELECT_EXTRACT_AND_COLLAPSE,
    CONTEXT_SELECT_FILTER_BY_TOOL_KEY,
    CONTEXT_SELECT_KEEP_BY_TAG,
    CONTEXT_SELECT_PROMOTE_AND_STRIP,
    CONTEXT_SELECT_SPLIT_AND_PROMOTE,
    CONTEXT_STRUCTURAL_TOOL_KEYS,
    CONTEXT_STRUCT_COLLAPSE_CHAIN,
    CONTEXT_STRUCT_DEDUPLICATE,
    CONTEXT_STRUCT_FOLD_BY_TOOL_KEY,
    CONTEXT_STRUCT_MERGE_SECTIONS,
    CONTEXT_STRUCT_REDACT,
    CONTEXT_STRUCT_REORDER,
    CONTEXT_STRUCT_STRIP_OUTPUTS,
    CONTEXT_STRUCT_TRUNCATE,
    CONTEXT_STRUCT_WINDOW_SLICE,
    CONTEXT_SUMMARIZATION_TOOL_KEYS,
    CONTEXT_SUMMARIZE_CHRONOLOGICAL,
    CONTEXT_SUMMARIZE_DECISIONS,
    CONTEXT_SUMMARIZE_ENTITIES,
    CONTEXT_SUMMARIZE_ERRORS,
    CONTEXT_SUMMARIZE_EXTRACTED_DATA,
    CONTEXT_SUMMARIZE_GOALS_AND_GAPS,
    CONTEXT_SUMMARIZE_HEADLINE,
    CONTEXT_SUMMARIZE_OPEN_QUESTIONS,
    CONTEXT_SUMMARIZE_STATE_SNAPSHOT,
    CONTEXT_TOOL_KEYS,
    CONTEXT_TRANSCRIPT_INJECTION_TOOL_KEYS,
    RegisteredTool,
    ToolDefinition,
)

_ALLOWED_CONTEXT_KINDS = frozenset(
    {
        "parameter",
        "message",
        "assistant",
        "tool_call",
        "tool_result",
        "summary",
        "context",
    }
)
_CONTEXT_WINDOW_PROPERTY: dict[str, object] = {
    "type": "array",
    "description": "An ordered list of normalized agent context entries.",
    "items": {"type": "object"},
}


@dataclass(frozen=True, slots=True)
class ContextToolRuntime:
    """Callbacks the context-tool family needs from the live agent runtime."""

    get_context_window: Callable[[], AgentContextWindow]
    get_runtime_state: Callable[[], AgentContextRuntimeState]
    save_runtime_state: Callable[[], None]
    refresh_parameters: Callable[[], Any]
    get_reset_count: Callable[[], int]
    get_cycle_index: Callable[[], int]
    get_system_prompt: Callable[[], str] | None = None
    run_model_subcall: Callable[..., str] | None = None


def create_context_tools(
    *,
    get_context_window: Callable[[], AgentContextWindow] | None = None,
    get_runtime_state: Callable[[], AgentContextRuntimeState] | None = None,
    save_runtime_state: Callable[[], None] | None = None,
    refresh_parameters: Callable[[], Any] | None = None,
    get_reset_count: Callable[[], int] | None = None,
    get_cycle_index: Callable[[], int] | None = None,
    get_system_prompt: Callable[[], str] | None = None,
    run_model_subcall: Callable[..., str] | None = None,
) -> tuple[RegisteredTool, ...]:
    runtime = _resolve_runtime(
        get_context_window=get_context_window,
        get_runtime_state=get_runtime_state,
        save_runtime_state=save_runtime_state,
        refresh_parameters=refresh_parameters,
        get_reset_count=get_reset_count,
        get_cycle_index=get_cycle_index,
        get_system_prompt=get_system_prompt,
        run_model_subcall=run_model_subcall,
    )

    from .injection import create_context_injection_tools
    from .parameter import create_context_parameter_tools
    from .selective import create_context_selective_tools
    from .structural import create_context_structural_tools
    from .summarization import create_context_summarization_tools

    return (
        *create_context_summarization_tools(runtime),
        *create_context_structural_tools(runtime),
        *create_context_selective_tools(runtime),
        *create_context_parameter_tools(runtime),
        *create_context_injection_tools(runtime),
    )


def build_tool_definition(
    *,
    key: str,
    name: str,
    description: str,
    properties: dict[str, Any],
    required: Sequence[str] = (),
) -> ToolDefinition:
    return ToolDefinition(
        key=key,
        name=name,
        description=description,
        input_schema={
            "type": "object",
            "properties": deepcopy(properties),
            "required": list(required),
            "additionalProperties": False,
        },
    )


def normalize_context_window(context_window: Sequence[Mapping[str, Any]]) -> AgentContextWindow:
    normalized: AgentContextWindow = []
    for index, entry in enumerate(context_window):
        if not isinstance(entry, Mapping):
            raise ValueError(f"Context entry at index {index} must be a mapping.")
        kind = entry.get("kind")
        if kind not in _ALLOWED_CONTEXT_KINDS:
            raise ValueError(f"Unsupported context entry kind '{kind}' at index {index}.")
        normalized.append(deepcopy(dict(entry)))
    return normalized


def current_context_window(runtime: ContextToolRuntime) -> AgentContextWindow:
    return normalize_context_window(runtime.get_context_window())


def split_context_window(context_window: Sequence[Mapping[str, Any]]) -> tuple[list[AgentContextEntry], list[AgentContextEntry]]:
    normalized = normalize_context_window(context_window)
    parameter_entries: list[AgentContextEntry] = []
    transcript_entries: list[AgentContextEntry] = []
    for entry in normalized:
        if entry["kind"] == "parameter" and not transcript_entries:
            parameter_entries.append(entry)
        else:
            transcript_entries.append(entry)
    return parameter_entries, transcript_entries


def rebuild_context_window(
    parameter_entries: Sequence[Mapping[str, Any]],
    transcript_entries: Sequence[Mapping[str, Any]],
) -> AgentContextWindow:
    return [
        *normalize_context_window(parameter_entries),
        *normalize_context_window(transcript_entries),
    ]


def context_window_property() -> dict[str, object]:
    return deepcopy(_CONTEXT_WINDOW_PROPERTY)


def serialize_context_entries(entries: Sequence[Mapping[str, Any]]) -> str:
    rendered: list[str] = []
    for entry in normalize_context_window(entries):
        kind = entry["kind"]
        if kind == "parameter":
            rendered.append(f"[PARAMETER] {entry.get('label', 'Parameter')}\n{entry.get('content', '')}")
        elif kind in {"assistant", "message"}:
            role = entry.get("role", "assistant")
            rendered.append(f"[{str(role).upper()}]\n{entry.get('content', '')}")
        elif kind == "tool_call":
            rendered.append(
                f"[TOOL CALL] {context_entry_tool_key(entry) or 'tool'}\n"
                f"{json.dumps(entry.get('arguments', entry.get('content', {})), sort_keys=True, default=str)}"
            )
        elif kind == "tool_result":
            rendered.append(
                f"[TOOL RESULT] {context_entry_tool_key(entry) or 'tool'}\n"
                f"{json.dumps(entry.get('output', entry.get('content', '')), sort_keys=True, default=str)}"
            )
        elif kind == "context":
            rendered.append(f"[CONTEXT] {entry.get('label', 'Context')}\n{entry.get('content', '')}")
        else:
            rendered.append(f"[SUMMARY]\n{entry.get('content', '')}")
    return "\n\n".join(rendered)


def context_window_tokens(context_window: Sequence[Mapping[str, Any]]) -> int:
    return estimate_text_tokens(serialize_context_entries(context_window))


def context_entry_tool_key(entry: Mapping[str, Any]) -> str | None:
    tool_key = entry.get("tool_key")
    if isinstance(tool_key, str) and tool_key.strip():
        return tool_key.strip()
    content = entry.get("content")
    if isinstance(content, str) and "\n" in content:
        first_line = content.splitlines()[0].strip()
        return first_line or None
    return None


def transcript_entry_text(entry: Mapping[str, Any]) -> str:
    return serialize_context_entries([entry])


def output_contains_error(entry: Mapping[str, Any]) -> bool:
    output = entry.get("output")
    if isinstance(output, Mapping):
        return "error" in output
    content = entry.get("content")
    if isinstance(content, str):
        return '"error"' in content or content.lower().startswith("error")
    return False


def require_model_runner(runtime: ContextToolRuntime) -> Callable[..., str]:
    if runtime.run_model_subcall is None:
        raise RuntimeError("This context tool requires a bound model subcall runner.")
    return runtime.run_model_subcall


def apply_memory_refresh(runtime: ContextToolRuntime) -> None:
    runtime.save_runtime_state()
    runtime.refresh_parameters()


def coerce_int(arguments: dict[str, Any], key: str, *, default: int | None = None) -> int:
    if key not in arguments:
        if default is None:
            raise ValueError(f"The '{key}' argument is required.")
        return default
    value = arguments[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"The '{key}' argument must be an integer.")
    return value


def coerce_bool(arguments: dict[str, Any], key: str, *, default: bool) -> bool:
    value = arguments.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"The '{key}' argument must be a boolean.")
    return value


def coerce_string(arguments: dict[str, Any], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"The '{key}' argument must be a non-empty string.")
    return value


def coerce_optional_string(arguments: dict[str, Any], key: str) -> str | None:
    if key not in arguments or arguments[key] is None:
        return None
    value = arguments[key]
    if not isinstance(value, str):
        raise ValueError(f"The '{key}' argument must be a string when provided.")
    return value


def coerce_string_list(arguments: dict[str, Any], key: str) -> list[str]:
    value = arguments.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"The '{key}' argument must be an array of strings.")
    return [str(item) for item in value]


def copy_entry(entry: Mapping[str, Any]) -> AgentContextEntry:
    return deepcopy(dict(entry))


def _resolve_runtime(
    *,
    get_context_window: Callable[[], AgentContextWindow] | None,
    get_runtime_state: Callable[[], AgentContextRuntimeState] | None,
    save_runtime_state: Callable[[], None] | None,
    refresh_parameters: Callable[[], Any] | None,
    get_reset_count: Callable[[], int] | None,
    get_cycle_index: Callable[[], int] | None,
    get_system_prompt: Callable[[], str] | None,
    run_model_subcall: Callable[..., str] | None,
) -> ContextToolRuntime:
    runtime_state = AgentContextRuntimeState()
    return ContextToolRuntime(
        get_context_window=get_context_window or (lambda: []),
        get_runtime_state=get_runtime_state or (lambda: runtime_state),
        save_runtime_state=save_runtime_state or (lambda: None),
        refresh_parameters=refresh_parameters or (lambda: None),
        get_reset_count=get_reset_count or (lambda: 0),
        get_cycle_index=get_cycle_index or (lambda: 0),
        get_system_prompt=get_system_prompt,
        run_model_subcall=run_model_subcall,
    )


__all__ = [
    "CONTEXT_COMPACTION_TOOL_KEYS",
    "CONTEXT_INJECT_ASSISTANT_NOTE",
    "CONTEXT_INJECT_CONTEXT_BLOCK",
    "CONTEXT_INJECT_HANDOFF_BRIEF",
    "CONTEXT_INJECT_PROGRESS_MARKER",
    "CONTEXT_INJECT_REPLAY_MEMORY",
    "CONTEXT_INJECT_SYNTHETIC_TOOL_RESULT",
    "CONTEXT_INJECT_TASK_REMINDER",
    "CONTEXT_INJECT_TOOL_CALL_PAIR",
    "CONTEXT_PARAMETER_TOOL_KEYS",
    "CONTEXT_PARAM_APPEND_MEMORY_FIELD",
    "CONTEXT_PARAM_BULK_WRITE_MEMORY",
    "CONTEXT_PARAM_CLEAR_MEMORY_FIELD",
    "CONTEXT_PARAM_INJECT_DIRECTIVE",
    "CONTEXT_PARAM_INJECT_SECTION",
    "CONTEXT_PARAM_OVERWRITE_MEMORY_FIELD",
    "CONTEXT_PARAM_UPDATE_SECTION",
    "CONTEXT_PARAM_WRITE_ONCE_MEMORY_FIELD",
    "CONTEXT_SELECTIVE_TOOL_KEYS",
    "CONTEXT_SELECT_ANNOTATE_ENTRY",
    "CONTEXT_SELECT_CHECKPOINT",
    "CONTEXT_SELECT_EXTRACT_AND_COLLAPSE",
    "CONTEXT_SELECT_FILTER_BY_TOOL_KEY",
    "CONTEXT_SELECT_KEEP_BY_TAG",
    "CONTEXT_SELECT_PROMOTE_AND_STRIP",
    "CONTEXT_SELECT_SPLIT_AND_PROMOTE",
    "CONTEXT_STRUCTURAL_TOOL_KEYS",
    "CONTEXT_STRUCT_COLLAPSE_CHAIN",
    "CONTEXT_STRUCT_DEDUPLICATE",
    "CONTEXT_STRUCT_FOLD_BY_TOOL_KEY",
    "CONTEXT_STRUCT_MERGE_SECTIONS",
    "CONTEXT_STRUCT_REDACT",
    "CONTEXT_STRUCT_REORDER",
    "CONTEXT_STRUCT_STRIP_OUTPUTS",
    "CONTEXT_STRUCT_TRUNCATE",
    "CONTEXT_STRUCT_WINDOW_SLICE",
    "CONTEXT_SUMMARIZATION_TOOL_KEYS",
    "CONTEXT_SUMMARIZE_CHRONOLOGICAL",
    "CONTEXT_SUMMARIZE_DECISIONS",
    "CONTEXT_SUMMARIZE_ENTITIES",
    "CONTEXT_SUMMARIZE_ERRORS",
    "CONTEXT_SUMMARIZE_EXTRACTED_DATA",
    "CONTEXT_SUMMARIZE_GOALS_AND_GAPS",
    "CONTEXT_SUMMARIZE_HEADLINE",
    "CONTEXT_SUMMARIZE_OPEN_QUESTIONS",
    "CONTEXT_SUMMARIZE_STATE_SNAPSHOT",
    "CONTEXT_TOOL_KEYS",
    "CONTEXT_TRANSCRIPT_INJECTION_TOOL_KEYS",
    "ContextToolRuntime",
    "apply_memory_refresh",
    "build_tool_definition",
    "coerce_bool",
    "coerce_int",
    "coerce_optional_string",
    "coerce_string",
    "coerce_string_list",
    "context_entry_tool_key",
    "context_window_property",
    "context_window_tokens",
    "copy_entry",
    "create_context_tools",
    "current_context_window",
    "normalize_context_window",
    "output_contains_error",
    "rebuild_context_window",
    "require_model_runner",
    "serialize_context_entries",
    "split_context_window",
    "transcript_entry_text",
]
