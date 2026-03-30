"""
===============================================================================
File: harnessiq/tools/context/executors/structural.py

What this file does:
- Implements part of the context-tool system that rewrites, summarizes, or
  annotates an agent context window.
- Execution logic for structural context tools.

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
import re
from typing import Any

from .. import (
    ContextToolRuntime,
    coerce_bool,
    coerce_non_negative_int,
    coerce_optional_string,
    coerce_positive_int,
    coerce_string,
    coerce_string_list,
    context_entry_tool_key,
    copy_entry,
    current_context_window,
    output_contains_error,
    rebuild_context_window,
    require_model_runner,
    serialize_context_entries,
    split_context_window,
)


def truncate(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    keep_last = coerce_positive_int(arguments, "keep_last")
    parameter_entries, transcript_entries = split_context_window(current_context_window(runtime))
    if len(transcript_entries) <= keep_last:
        return {"context_window": rebuild_context_window(parameter_entries, transcript_entries)}
    dropped = len(transcript_entries) - keep_last
    synthetic = {
        "kind": "context",
        "label": "TRUNCATE",
        "content": f"[{dropped} entries dropped by truncate]",
    }
    kept = [synthetic, *transcript_entries[-keep_last:]]
    return {"context_window": rebuild_context_window(parameter_entries, kept)}


def strip_outputs(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    tool_keys = set(coerce_string_list(arguments, "tool_keys"))
    preserve_errors = coerce_bool(arguments, "preserve_errors", default=True)
    parameter_entries, transcript_entries = split_context_window(current_context_window(runtime))
    rewritten: list[dict[str, Any]] = []
    for entry in transcript_entries:
        if entry["kind"] != "tool_result":
            rewritten.append(copy_entry(entry))
            continue
        tool_key = context_entry_tool_key(entry)
        if tool_keys and tool_key not in tool_keys:
            rewritten.append(copy_entry(entry))
            continue
        if preserve_errors and output_contains_error(entry):
            rewritten.append(copy_entry(entry))
            continue
        stripped = copy_entry(entry)
        stripped["content"] = "[output stripped - see memory zone]"
        stripped["output"] = "[output stripped - see memory zone]"
        rewritten.append(stripped)
    return {"context_window": rebuild_context_window(parameter_entries, rewritten)}


def deduplicate(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    tool_keys = set(coerce_string_list(arguments, "tool_keys"))
    similarity_threshold = arguments.get("similarity_threshold", 0.9)
    if isinstance(similarity_threshold, bool) or not isinstance(similarity_threshold, (int, float)):
        raise ValueError("The 'similarity_threshold' argument must be numeric.")
    max_gap = coerce_non_negative_int(arguments, "max_gap", default=2)

    parameter_entries, transcript_entries = split_context_window(current_context_window(runtime))
    kept: list[dict[str, Any]] = []

    for entry in transcript_entries:
        candidate = copy_entry(entry)
        if candidate["kind"] != "tool_result":
            kept.append(candidate)
            continue
        tool_key = context_entry_tool_key(candidate)
        if tool_keys and tool_key not in tool_keys:
            kept.append(candidate)
            continue
        matched_index = _find_duplicate_match(kept, tool_key=tool_key, candidate=candidate, threshold=float(similarity_threshold), max_gap=max_gap)
        if matched_index is None:
            kept.append(candidate)
            continue
        duplicate_count = 1
        previous = kept.pop(matched_index)
        previous_count = _extract_duplicate_count(previous)
        if previous_count:
            duplicate_count += previous_count
        annotated = _annotate_duplicate(candidate, duplicate_count)
        kept.append(annotated)

    return {"context_window": rebuild_context_window(parameter_entries, kept)}


def reorder(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    entry_index = coerce_non_negative_int(arguments, "entry_index")
    parameter_entries, transcript_entries = split_context_window(current_context_window(runtime))
    if entry_index >= len(transcript_entries):
        raise ValueError("The 'entry_index' argument is outside the transcript range.")
    entry = copy_entry(transcript_entries[entry_index])
    rewritten = [copy_entry(item) for idx, item in enumerate(transcript_entries) if idx != entry_index]
    rewritten.append(entry)
    return {"context_window": rebuild_context_window(parameter_entries, rewritten)}


def collapse_chain(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    start_index = coerce_non_negative_int(arguments, "start_index")
    end_index = coerce_non_negative_int(arguments, "end_index")
    summary = coerce_string(arguments, "summary")
    if end_index < start_index:
        raise ValueError("The 'end_index' argument must be greater than or equal to 'start_index'.")
    parameter_entries, transcript_entries = split_context_window(current_context_window(runtime))
    if end_index >= len(transcript_entries):
        raise ValueError("The provided range is outside the transcript.")
    rewritten = [
        *[copy_entry(entry) for entry in transcript_entries[:start_index]],
        {"kind": "context", "label": "COLLAPSED CHAIN", "content": summary},
        *[copy_entry(entry) for entry in transcript_entries[end_index + 1 :]],
    ]
    return {"context_window": rebuild_context_window(parameter_entries, rewritten)}


def redact(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    patterns = coerce_string_list(arguments, "patterns")
    if not patterns:
        raise ValueError("The 'patterns' argument must contain at least one string.")
    redaction_label = arguments.get("redaction_label", "[redacted]")
    if not isinstance(redaction_label, str):
        raise ValueError("The 'redaction_label' argument must be a string.")
    parameter_entries, transcript_entries = split_context_window(current_context_window(runtime))
    rewritten = [_redact_entry(copy_entry(entry), patterns=patterns, label=redaction_label) for entry in transcript_entries]
    return {"context_window": rebuild_context_window(parameter_entries, rewritten)}


def merge_sections(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    range_a = _coerce_index_range(arguments, "range_a")
    range_b = _coerce_index_range(arguments, "range_b")
    merge_label = arguments.get("merge_label", "MERGED SECTION")
    if not isinstance(merge_label, str):
        raise ValueError("The 'merge_label' argument must be a string when provided.")
    model_override = coerce_optional_string(arguments, "model_override")
    lower, upper = sorted((range_a, range_b), key=lambda item: item[0])
    parameter_entries, transcript_entries = split_context_window(current_context_window(runtime))
    if lower[1] >= len(transcript_entries) or upper[1] >= len(transcript_entries):
        raise ValueError("The provided merge ranges are outside the transcript.")
    selected = [
        *transcript_entries[lower[0] : lower[1] + 1],
        *transcript_entries[upper[0] : upper[1] + 1],
    ]
    merged_text = require_model_runner(runtime)(
        system_prompt=(
            "Merge the two transcript fragments into one coherent summary block. "
            "Preserve net effect, decisions, and important outputs. Return plain text only."
        ),
        transcript_text=serialize_context_entries(selected),
        model_override=model_override,
    )
    rewritten = [
        *[copy_entry(entry) for entry in transcript_entries[: lower[0]]],
        {"kind": "context", "label": merge_label or "MERGED SECTION", "content": merged_text},
        *[copy_entry(entry) for entry in transcript_entries[lower[1] + 1 : upper[0]]],
        *[copy_entry(entry) for entry in transcript_entries[upper[1] + 1 :]],
    ]
    return {"context_window": rebuild_context_window(parameter_entries, rewritten)}


def window_slice(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    start_index = coerce_non_negative_int(arguments, "start_index")
    end_index = coerce_non_negative_int(arguments, "end_index")
    preserve_latest_n = coerce_non_negative_int(arguments, "preserve_latest_n", default=0)
    if end_index < start_index:
        raise ValueError("The 'end_index' argument must be greater than or equal to 'start_index'.")
    parameter_entries, transcript_entries = split_context_window(current_context_window(runtime))
    if end_index >= len(transcript_entries):
        raise ValueError("The requested slice is outside the transcript.")
    selected_indices = set(range(start_index, end_index + 1))
    sliced = [copy_entry(entry) for idx, entry in enumerate(transcript_entries) if idx in selected_indices]
    if preserve_latest_n:
        latest_indices = range(max(0, len(transcript_entries) - preserve_latest_n), len(transcript_entries))
        for idx in latest_indices:
            if idx not in selected_indices:
                sliced.append(copy_entry(transcript_entries[idx]))
    return {"context_window": rebuild_context_window(parameter_entries, sliced)}


def fold_by_tool_key(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    tool_key = coerce_string(arguments, "tool_key")
    keep_latest_n = coerce_non_negative_int(arguments, "keep_latest_n", default=1)
    model_override = coerce_optional_string(arguments, "model_override")
    parameter_entries, transcript_entries = split_context_window(current_context_window(runtime))
    matching_indices = [
        index
        for index, entry in enumerate(transcript_entries)
        if context_entry_tool_key(entry) == tool_key
    ]
    if not matching_indices:
        return {"context_window": rebuild_context_window(parameter_entries, transcript_entries)}

    latest_matching = set(matching_indices[-keep_latest_n:] if keep_latest_n else [])
    fold_indices = [index for index in matching_indices if index not in latest_matching]
    if not fold_indices:
        return {"context_window": rebuild_context_window(parameter_entries, transcript_entries)}
    folded_text = require_model_runner(runtime)(
        system_prompt=(
            f"Summarize the combined output and effect of the transcript entries for tool key '{tool_key}'. "
            "Return one compact paragraph."
        ),
        transcript_text=serialize_context_entries([transcript_entries[index] for index in fold_indices]),
        model_override=model_override,
    )
    insertion_index = fold_indices[0]
    rewritten: list[dict[str, Any]] = []
    for index, entry in enumerate(transcript_entries):
        if index == insertion_index:
            rewritten.append({"kind": "context", "label": f"FOLDED {tool_key}", "content": folded_text})
        if index in fold_indices:
            continue
        rewritten.append(copy_entry(entry))
    return {"context_window": rebuild_context_window(parameter_entries, rewritten)}


def _find_duplicate_match(
    entries: list[dict[str, Any]],
    *,
    tool_key: str | None,
    candidate: dict[str, Any],
    threshold: float,
    max_gap: int,
) -> int | None:
    candidate_text = _dedupe_text(candidate)
    for index in range(len(entries) - 1, -1, -1):
        existing = entries[index]
        if existing["kind"] != "tool_result":
            continue
        if context_entry_tool_key(existing) != tool_key:
            continue
        if len(entries) - index - 1 > max_gap:
            break
        if _similarity(candidate_text, _dedupe_text(existing)) >= threshold:
            return index
    return None


def _dedupe_text(entry: dict[str, Any]) -> str:
    output = entry.get("output", entry.get("content", ""))
    if isinstance(output, str):
        return output
    return json.dumps(output, sort_keys=True, default=str)


def _extract_duplicate_count(entry: dict[str, Any]) -> int:
    output = entry.get("output")
    if isinstance(output, dict):
        count = output.get("duplicates_removed")
        if isinstance(count, int):
            return count
    metadata = entry.get("metadata")
    if isinstance(metadata, dict):
        count = metadata.get("duplicates_removed")
        if isinstance(count, int):
            return count
    return 0


def _annotate_duplicate(entry: dict[str, Any], duplicate_count: int) -> dict[str, Any]:
    annotated = copy_entry(entry)
    output = annotated.get("output")
    if isinstance(output, dict):
        output["duplicates_removed"] = duplicate_count
    else:
        annotated["output"] = {
            "duplicates_removed": duplicate_count,
            "latest_value": output,
        }
    metadata = dict(annotated.get("metadata", {})) if isinstance(annotated.get("metadata"), dict) else {}
    metadata["duplicates_removed"] = duplicate_count
    annotated["metadata"] = metadata
    return annotated


def _similarity(left: str, right: str) -> float:
    left_tokens = set(re.findall(r"\w+", left.lower()))
    right_tokens = set(re.findall(r"\w+", right.lower()))
    if not left_tokens and not right_tokens:
        return 1.0
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = len(left_tokens.intersection(right_tokens))
    baseline = max(len(left_tokens), len(right_tokens))
    return overlap / baseline


def _redact_entry(entry: dict[str, Any], *, patterns: list[str], label: str) -> dict[str, Any]:
    for key, value in list(entry.items()):
        entry[key] = _redact_value(value, patterns=patterns, label=label)
    return entry


def _redact_value(value: Any, *, patterns: list[str], label: str) -> Any:
    if isinstance(value, str):
        redacted = value
        for pattern in patterns:
            redacted = re.sub(re.escape(pattern), label, redacted)
        return redacted
    if isinstance(value, list):
        return [_redact_value(item, patterns=patterns, label=label) for item in value]
    if isinstance(value, dict):
        return {
            _redact_value(key, patterns=patterns, label=label): _redact_value(item, patterns=patterns, label=label)
            for key, item in value.items()
        }
    return value


def _coerce_index_range(arguments: dict[str, Any], key: str) -> tuple[int, int]:
    raw = arguments.get(key)
    if not isinstance(raw, list) or len(raw) != 2 or not all(isinstance(item, int) and not isinstance(item, bool) for item in raw):
        raise ValueError(f"The '{key}' argument must be a two-item integer array.")
    start = coerce_non_negative_int({key: raw[0]}, key)
    end = coerce_non_negative_int({key: raw[1]}, key)
    if end < start:
        raise ValueError(f"The '{key}' argument must use [start_index, end_index] with end >= start.")
    return start, end


__all__ = [
    "collapse_chain",
    "deduplicate",
    "fold_by_tool_key",
    "merge_sections",
    "redact",
    "reorder",
    "strip_outputs",
    "truncate",
    "window_slice",
]
