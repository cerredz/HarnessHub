"""
===============================================================================
File: harnessiq/tools/context/executors/catalog.py

What this file does:
- Implements part of the context-tool system that rewrites, summarizes, or
  annotates an agent context window.
- Additional catalog context-tool executors.

Use cases:
- Use these helpers when a runtime needs deterministic context compaction or
  injection behavior.

How to use it:
- Import the definitions or executors from this module through the context-tool
  catalog rather than wiring ad hoc context mutations inline.

Intent:
- Keep context-window manipulation explicit and reusable so long-running agents
  can manage token pressure predictably.
===============================================================================
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from harnessiq.shared.agents import DEFAULT_AGENT_MAX_TOKENS

from .. import (
    ContextToolRuntime,
    coerce_bool,
    coerce_non_negative_int,
    coerce_optional_string,
    coerce_string,
    coerce_string_list,
    context_entry_tool_key,
    context_window_tokens,
    copy_entry,
    current_context_window,
    rebuild_context_window,
    split_context_window,
)


def summarize_transcript(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    # The summary payload deliberately separates completed actions, tool results,
    # and recent errors so a caller can compact the transcript without losing the
    # pieces of state most useful for the next reasoning step.
    detail = coerce_optional_string(arguments, "detail_level") or "standard"
    parameter_entries, transcript_entries = split_context_window(current_context_window(runtime))
    completed_actions = [entry.get("content", "") for entry in transcript_entries if entry["kind"] in {"assistant", "summary"} and entry.get("content")]
    tool_results = []
    errors = []
    for entry in transcript_entries:
        if entry["kind"] == "tool_result":
            tool_key = context_entry_tool_key(entry) or "tool"
            output = entry.get("output")
            summary = str(output)[:160]
            tool_results.append({"tool_key": tool_key, "summary": summary})
            if isinstance(output, dict) and "error" in output:
                errors.append({"tool_key": tool_key, "error": output["error"]})
    payload = {
        "completed_actions": completed_actions[-8:] if detail == "minimal" else completed_actions,
        "tool_calls": [] if detail == "minimal" else tool_results,
        "errors": errors if detail == "full" else errors[:3],
        "next_recommended_action": _next_action_hint(transcript_entries),
        "token_count": context_window_tokens(parameter_entries + transcript_entries),
    }
    return payload


def prune_tool_results(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    # Result pruning preserves the latest matching tool results while replacing
    # older ones with an explicit marker. That retains the fact that work
    # happened without paying the full token cost of every historical payload.
    keep_last_n = coerce_non_negative_int(arguments, "keep_last_n", default=3)
    tool_filter = set(coerce_string_list(arguments, "tool_filter"))
    replacement = coerce_optional_string(arguments, "replacement_text") or "[result pruned - content processed]"
    parameter_entries, transcript_entries = split_context_window(current_context_window(runtime))
    result_indices = [index for index, entry in enumerate(transcript_entries) if entry["kind"] == "tool_result" and (not tool_filter or context_entry_tool_key(entry) in tool_filter)]
    keep_indices = set(result_indices[-keep_last_n:]) if keep_last_n else set()
    rewritten = []
    for index, entry in enumerate(transcript_entries):
        if index in keep_indices or entry["kind"] != "tool_result" or (tool_filter and context_entry_tool_key(entry) not in tool_filter):
            rewritten.append(copy_entry(entry))
            continue
        redacted = copy_entry(entry)
        redacted["output"] = replacement
        redacted["content"] = replacement
        rewritten.append(redacted)
    return {"context_window": rebuild_context_window(parameter_entries, rewritten)}


def estimate_window_pressure(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    # Pressure estimates turn raw token counts into discrete operating guidance
    # so agents and hooks can make deterministic compaction decisions instead of
    # guessing from the transcript size alone.
    planned = arguments.get("planned_action_tokens")
    if planned is not None and (isinstance(planned, bool) or not isinstance(planned, int)):
        raise ValueError("The 'planned_action_tokens' argument must be an integer when provided.")
    limit = arguments.get("reset_token_limit")
    if limit is None:
        limit = int(DEFAULT_AGENT_MAX_TOKENS * 0.9)
    elif isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("The 'reset_token_limit' argument must be an integer when provided.")
    window = current_context_window(runtime)
    total_tokens = context_window_tokens(window)
    projected = total_tokens + (planned or 0)
    remaining = max(0, limit - projected)
    ratio = projected / limit if limit else 1.0
    if ratio >= 1:
        pressure = "critical"
        recommendation = "consolidate_and_reset"
    elif ratio >= 0.85:
        pressure = "high"
        recommendation = "compact"
    elif ratio >= 0.6:
        pressure = "moderate"
        recommendation = "continue"
    else:
        pressure = "low"
        recommendation = "continue"
    return {"estimated_tokens": total_tokens, "projected_tokens": projected, "remaining_capacity": remaining, "pressure_level": pressure, "recommendation": recommendation}


def trim_oldest_entries(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    count = coerce_non_negative_int(arguments, "n")
    min_preserve = coerce_non_negative_int(arguments, "min_preserve", default=4)
    summarize = coerce_bool(arguments, "summarize_dropped", default=False)
    parameter_entries, transcript_entries = split_context_window(current_context_window(runtime))
    removable = max(0, len(transcript_entries) - min_preserve)
    drop_count = min(count, removable)
    dropped = transcript_entries[:drop_count]
    kept = [copy_entry(entry) for entry in transcript_entries[drop_count:]]
    if summarize and dropped:
        kinds = Counter(entry["kind"] for entry in dropped)
        kept.insert(0, {"kind": "assistant", "content": f"[TRIMMED] dropped {drop_count} oldest entries: {dict(kinds)}"})
    return {"context_window": rebuild_context_window(parameter_entries, kept)}


def handoff_brief(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": coerce_optional_string(arguments, "schema_version") or "1.0",
        "continuation_pointer": coerce_string(arguments, "continuation_pointer"),
        "task_goal": coerce_string(arguments, "task_goal"),
        "completed_outputs": arguments.get("completed_outputs", []),
        "active_constraints": coerce_string_list(arguments, "active_constraints"),
        "blockers": arguments.get("blockers", []),
        "recent_decisions": arguments.get("recent_decisions", []),
    }


def collapse_repeated_calls(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    # Repeated tool-call runs often come from retry loops or idempotent probing.
    # Collapsing exact repeats preserves the latest representative call while
    # encoding the repetition count as metadata for downstream inspection.
    minimum = coerce_non_negative_int(arguments, "min_repetitions", default=3)
    tool_filter = set(coerce_string_list(arguments, "tool_filter"))
    parameter_entries, transcript_entries = split_context_window(current_context_window(runtime))
    rewritten: list[dict[str, Any]] = []
    index = 0
    groups_collapsed = 0
    token_savings = 0
    while index < len(transcript_entries):
        current = transcript_entries[index]
        if current["kind"] != "tool_call" or (tool_filter and context_entry_tool_key(current) not in tool_filter):
            rewritten.append(copy_entry(current))
            index += 1
            continue
        run_end = index + 1
        while run_end < len(transcript_entries) and transcript_entries[run_end]["kind"] == "tool_call" and context_entry_tool_key(transcript_entries[run_end]) == context_entry_tool_key(current) and json.dumps(transcript_entries[run_end].get("arguments", {}), sort_keys=True, default=str) == json.dumps(current.get("arguments", {}), sort_keys=True, default=str):
            run_end += 1
        run_length = run_end - index
        if run_length >= minimum:
            groups_collapsed += 1
            token_savings += run_length - 1
            merged = copy_entry(current)
            merged["metadata"] = {**(merged.get("metadata") if isinstance(merged.get("metadata"), dict) else {}), "repetitions": run_length}
            rewritten.append(merged)
        else:
            rewritten.extend(copy_entry(entry) for entry in transcript_entries[index:run_end])
        index = run_end
    return {"context_window": rebuild_context_window(parameter_entries, rewritten), "groups_collapsed": groups_collapsed, "estimated_token_savings": token_savings}


def annotate_phase(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    parameter_entries, transcript_entries = split_context_window(current_context_window(runtime))
    transcript_entries = [*transcript_entries, {"kind": "context", "label": "PHASE", "content": f"{coerce_string(arguments, 'phase_name')}: {coerce_optional_string(arguments, 'description') or ''}".strip()}]
    return {"context_window": rebuild_context_window(parameter_entries, transcript_entries)}


def inject_reminder(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    label = coerce_optional_string(arguments, "label") or "POST-RESET ORIENTATION"
    parameter_entries, transcript_entries = split_context_window(current_context_window(runtime))
    transcript_entries = [*transcript_entries, {"kind": "assistant", "content": f"[{label}] {coerce_string(arguments, 'content')}"}]
    return {"context_window": rebuild_context_window(parameter_entries, transcript_entries)}


def _next_action_hint(transcript_entries: list[dict[str, Any]]) -> str:
    for entry in reversed(transcript_entries):
        if entry["kind"] == "assistant" and entry.get("content"):
            return str(entry["content"]).splitlines()[0][:200]
    return "Continue from the latest incomplete step."


__all__ = [
    "annotate_phase",
    "collapse_repeated_calls",
    "estimate_window_pressure",
    "handoff_brief",
    "inject_reminder",
    "prune_tool_results",
    "summarize_transcript",
    "trim_oldest_entries",
]
