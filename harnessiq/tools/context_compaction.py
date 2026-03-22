"""Context-window compaction helpers and registered tools."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Mapping, cast

from harnessiq.shared.agents import AgentContextEntry, AgentContextWindow
from harnessiq.shared.tools import (
    HEAVY_COMPACTION,
    LOG_COMPACTION,
    REMOVE_TOOL_RESULTS,
    REMOVE_TOOLS,
    RegisteredTool,
    ToolArguments,
    ToolDefinition,
)

ContextSummarizer = Callable[[AgentContextWindow], str | AgentContextEntry]
_ALLOWED_CONTEXT_KINDS = frozenset({"parameter", "message", "assistant", "tool_call", "tool_result", "summary", "context"})
_CONTEXT_WINDOW_PROPERTY: dict[str, object] = {
    "type": "array",
    "description": "An ordered list of normalized agent context entries.",
    "items": {"type": "object"},
}


def remove_tool_result_entries(context_window: list[Mapping[str, Any]]) -> AgentContextWindow:
    """Return a copy of the context window without tool-result entries."""
    normalized = _normalize_context_window(context_window)
    return [entry for entry in normalized if entry["kind"] != "tool_result"]


def remove_tool_entries(context_window: list[Mapping[str, Any]]) -> AgentContextWindow:
    """Return a copy of the context window without tool calls or tool results."""
    normalized = _normalize_context_window(context_window)
    return [entry for entry in normalized if entry["kind"] not in {"tool_call", "tool_result"}]


def heavy_compact_context(context_window: list[Mapping[str, Any]]) -> AgentContextWindow:
    """Preserve only the leading parameter block from the context window."""
    normalized = _normalize_context_window(context_window)
    return normalized[:_parameter_prefix_length(normalized)]


def apply_log_compaction(
    context_window: list[Mapping[str, Any]],
    summary: str | Mapping[str, Any],
) -> AgentContextWindow:
    """Preserve the parameter prefix and append a summary entry."""
    normalized = _normalize_context_window(context_window)
    preserved = normalized[:_parameter_prefix_length(normalized)]
    return [*preserved, _normalize_summary_entry(summary)]


def summarize_and_log_compact(
    context_window: list[Mapping[str, Any]],
    summarizer: ContextSummarizer,
) -> AgentContextWindow:
    """Summarize the full window through an injected callable, then compact it."""
    normalized = _normalize_context_window(context_window)
    summary = summarizer(deepcopy(normalized))
    return apply_log_compaction(normalized, summary)


def create_context_compaction_tools(
    *,
    log_summarizer: ContextSummarizer | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the registered tool set for context compaction."""
    return (
        RegisteredTool(
            definition=ToolDefinition(
                key=REMOVE_TOOL_RESULTS,
                name="remove_tool_results",
                description="Remove all tool-result entries from an agent context window.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "context_window": _context_window_property(),
                    },
                    "required": ["context_window"],
                    "additionalProperties": False,
                },
            ),
            handler=_remove_tool_results,
        ),
        RegisteredTool(
            definition=ToolDefinition(
                key=REMOVE_TOOLS,
                name="remove_tools",
                description="Remove all tool-call and tool-result entries from an agent context window.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "context_window": _context_window_property(),
                    },
                    "required": ["context_window"],
                    "additionalProperties": False,
                },
            ),
            handler=_remove_tools,
        ),
        RegisteredTool(
            definition=ToolDefinition(
                key=HEAVY_COMPACTION,
                name="heavy_compaction",
                description="Preserve only the leading parameter entries in an agent context window.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "context_window": _context_window_property(),
                    },
                    "required": ["context_window"],
                    "additionalProperties": False,
                },
            ),
            handler=_heavy_compaction,
        ),
        RegisteredTool(
            definition=ToolDefinition(
                key=LOG_COMPACTION,
                name="log_compaction",
                description=(
                    "Append a summary after the leading parameter entries and drop the rest "
                    "of the prior context window."
                ),
                input_schema=_log_compaction_input_schema(log_summarizer is None),
            ),
            handler=_build_log_compaction_handler(log_summarizer),
        ),
    )


def _remove_tool_results(arguments: ToolArguments) -> dict[str, AgentContextWindow]:
    return {"context_window": remove_tool_result_entries(_require_context_window(arguments))}


def _remove_tools(arguments: ToolArguments) -> dict[str, AgentContextWindow]:
    return {"context_window": remove_tool_entries(_require_context_window(arguments))}


def _heavy_compaction(arguments: ToolArguments) -> dict[str, AgentContextWindow]:
    return {"context_window": heavy_compact_context(_require_context_window(arguments))}


def _log_compaction(arguments: ToolArguments) -> dict[str, AgentContextWindow]:
    return {
        "context_window": apply_log_compaction(
            _require_context_window(arguments),
            arguments["summary"],
        )
    }


def _summarizing_log_compaction(
    arguments: ToolArguments,
    summarizer: ContextSummarizer,
) -> dict[str, AgentContextWindow]:
    return {
        "context_window": summarize_and_log_compact(
            _require_context_window(arguments),
            summarizer,
        )
    }


def _build_log_compaction_handler(
    summarizer: ContextSummarizer | None,
) -> Callable[[ToolArguments], dict[str, AgentContextWindow]]:
    if summarizer is None:
        return _log_compaction
    return lambda arguments: _summarizing_log_compaction(arguments, summarizer)


def _require_context_window(arguments: ToolArguments) -> list[Mapping[str, Any]]:
    context_window = arguments["context_window"]
    if not isinstance(context_window, list):
        raise ValueError("The 'context_window' argument must be a list of context entries.")
    return cast(list[Mapping[str, Any]], context_window)


def _normalize_context_window(context_window: list[Mapping[str, Any]]) -> AgentContextWindow:
    normalized: AgentContextWindow = []
    for index, entry in enumerate(context_window):
        if not isinstance(entry, Mapping):
            raise ValueError(f"Context entry at index {index} must be a mapping.")
        kind = entry.get("kind")
        if kind not in _ALLOWED_CONTEXT_KINDS:
            raise ValueError(f"Unsupported context entry kind '{kind}' at index {index}.")
        normalized.append(cast(AgentContextEntry, deepcopy(dict(entry))))
    return normalized


def _normalize_summary_entry(summary: str | Mapping[str, Any]) -> AgentContextEntry:
    if isinstance(summary, str):
        return {"kind": "summary", "content": summary}
    if not isinstance(summary, Mapping):
        raise ValueError("The 'summary' argument must be a string or mapping.")
    entry = cast(AgentContextEntry, deepcopy(dict(summary)))
    if entry.get("kind") != "summary":
        raise ValueError("Summary mappings must use kind='summary'.")
    return entry


def _parameter_prefix_length(context_window: AgentContextWindow) -> int:
    count = 0
    for entry in context_window:
        if entry["kind"] != "parameter":
            break
        count += 1
    return count


def _context_window_property() -> dict[str, object]:
    return deepcopy(_CONTEXT_WINDOW_PROPERTY)


def _log_compaction_input_schema(require_summary: bool) -> dict[str, object]:
    properties: dict[str, object] = {
        "context_window": _context_window_property(),
    }
    required = ["context_window"]
    if require_summary:
        properties["summary"] = {
            "description": (
                "A summary generated by a separate LLM or agent pass, either as "
                "plain text or as a pre-built summary entry."
            ),
        }
        required.append("summary")
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


__all__ = [
    "ContextSummarizer",
    "apply_log_compaction",
    "create_context_compaction_tools",
    "heavy_compact_context",
    "remove_tool_entries",
    "remove_tool_result_entries",
    "summarize_and_log_compact",
]
