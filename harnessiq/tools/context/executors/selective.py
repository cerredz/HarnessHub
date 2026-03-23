"""Execution logic for selective context tools."""

from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import uuid4

from harnessiq.shared.agents import AgentContextCheckpoint

from .. import (
    ContextToolRuntime,
    apply_memory_refresh,
    coerce_bool,
    coerce_int,
    coerce_optional_string,
    coerce_string,
    context_entry_tool_key,
    context_window_tokens,
    copy_entry,
    current_context_window,
    rebuild_context_window,
    require_model_runner,
    serialize_context_entries,
    split_context_window,
)
from .parameter import append_memory_value, overwrite_memory_value


def extract_and_collapse(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    keep_indices = _coerce_indices(arguments, "keep_indices")
    collapse_label = arguments.get("collapse_label", "[prior entries collapsed]")
    if not isinstance(collapse_label, str):
        raise ValueError("The 'collapse_label' argument must be a string when provided.")
    parameter_entries, transcript_entries = split_context_window(current_context_window(runtime))
    keep_lookup = set(keep_indices)
    if max(keep_lookup) >= len(transcript_entries):
        raise ValueError("The 'keep_indices' argument references an entry outside the transcript.")
    dropped_count = len(transcript_entries) - len(keep_lookup)
    if dropped_count <= 0:
        return {"context_window": rebuild_context_window(parameter_entries, transcript_entries)}

    rewritten: list[dict[str, Any]] = []
    collapse_inserted = False
    for index, entry in enumerate(transcript_entries):
        if index in keep_lookup:
            if not collapse_inserted and index != 0:
                rewritten.append({"kind": "context", "label": "COLLAPSE", "content": collapse_label})
                collapse_inserted = True
            rewritten.append(copy_entry(entry))
            continue
        if not collapse_inserted:
            rewritten.append({"kind": "context", "label": "COLLAPSE", "content": collapse_label})
            collapse_inserted = True
    return {"context_window": rebuild_context_window(parameter_entries, rewritten)}


def filter_by_tool_key(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    keep_keys = set(_coerce_string_list(arguments, "keep_keys"))
    include_assistant_messages = coerce_bool(arguments, "include_assistant_messages", default=True)
    parameter_entries, transcript_entries = split_context_window(current_context_window(runtime))
    kept: list[dict[str, Any]] = []
    for entry in transcript_entries:
        tool_key = context_entry_tool_key(entry)
        if tool_key is not None and tool_key in keep_keys:
            kept.append(copy_entry(entry))
            continue
        if entry["kind"] in {"assistant", "message"} and include_assistant_messages:
            kept.append(copy_entry(entry))
    return {"context_window": rebuild_context_window(parameter_entries, kept)}


def promote_and_strip(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    entry_index = coerce_int(arguments, "entry_index")
    target_field = coerce_string(arguments, "target_field")
    update_rule = arguments.get("update_rule")
    if update_rule not in {"overwrite", "append"}:
        raise ValueError("The 'update_rule' argument must be overwrite or append.")
    current_window = current_context_window(runtime)
    parameter_entries, transcript_entries = split_context_window(current_window)
    if entry_index >= len(transcript_entries):
        raise ValueError("The 'entry_index' argument is outside the transcript.")
    promoted_text = serialize_context_entries([transcript_entries[entry_index]])
    if update_rule == "append":
        append_memory_value(runtime, field_name=target_field, value=promoted_text, timestamp=False)
    else:
        runtime.get_runtime_state().memory_field_rules.setdefault(target_field, "overwrite")
        overwrite_memory_value(runtime, field_name=target_field, value=promoted_text)
    apply_memory_refresh(runtime)
    refreshed_parameters, _ = split_context_window(current_context_window(runtime))
    rewritten = [copy_entry(entry) for idx, entry in enumerate(transcript_entries) if idx != entry_index]
    return {"context_window": rebuild_context_window(refreshed_parameters, rewritten)}


def annotate_entry(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    entry_index = coerce_int(arguments, "entry_index")
    annotation = coerce_string(arguments, "annotation")
    tag = coerce_optional_string(arguments, "tag")
    parameter_entries, transcript_entries = split_context_window(current_context_window(runtime))
    if entry_index >= len(transcript_entries):
        raise ValueError("The 'entry_index' argument is outside the transcript.")
    rewritten = [copy_entry(entry) for entry in transcript_entries]
    entry = rewritten[entry_index]
    content = str(entry.get("content", "")).rstrip()
    entry["content"] = f"{content} // AGENT NOTE: {annotation}" if content else f"AGENT NOTE: {annotation}"
    metadata = dict(entry.get("metadata", {})) if isinstance(entry.get("metadata"), dict) else {}
    metadata["annotation"] = annotation
    if tag:
        metadata["tag"] = tag
        entry["tag"] = tag
    entry["metadata"] = metadata
    return {"context_window": rebuild_context_window(parameter_entries, rewritten)}


def checkpoint(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    checkpoint_name = coerce_string(arguments, "checkpoint_name")
    description = coerce_optional_string(arguments, "description")
    context_window = current_context_window(runtime)
    checkpoint_key = f"checkpoint_{uuid4().hex[:12]}"
    runtime.get_runtime_state().checkpoints[checkpoint_key] = AgentContextCheckpoint(
        key=checkpoint_key,
        checkpoint_name=checkpoint_name,
        description=description,
        token_count=context_window_tokens(context_window),
        saved_at_reset=runtime.get_reset_count(),
        saved_at_cycle=runtime.get_cycle_index(),
        context_window=tuple(deepcopy(context_window)),
    )
    runtime.save_runtime_state()
    return {
        "checkpoint_key": checkpoint_key,
        "context_window": context_window,
        "token_count": context_window_tokens(context_window),
    }


def keep_by_tag(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    tag = coerce_string(arguments, "tag")
    collapse_dropped = coerce_bool(arguments, "collapse_dropped", default=True)
    parameter_entries, transcript_entries = split_context_window(current_context_window(runtime))
    kept: list[dict[str, Any]] = []
    dropped = 0
    for entry in transcript_entries:
        entry_tag = None
        if isinstance(entry.get("metadata"), dict):
            entry_tag = entry["metadata"].get("tag")
        if entry.get("tag") == tag or entry_tag == tag:
            kept.append(copy_entry(entry))
        else:
            dropped += 1
    if dropped and collapse_dropped:
        kept.insert(0, {"kind": "context", "label": "TAG FILTER", "content": f"[{dropped} entries without tag '{tag}' dropped]"})
    return {"context_window": rebuild_context_window(parameter_entries, kept)}


def split_and_promote(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    split_index = coerce_int(arguments, "split_index")
    target_field = coerce_string(arguments, "target_field")
    summarize_before = coerce_bool(arguments, "summarize_before", default=True)
    model_override = coerce_optional_string(arguments, "model_override")
    parameter_entries, transcript_entries = split_context_window(current_context_window(runtime))
    if split_index > len(transcript_entries):
        raise ValueError("The 'split_index' argument is outside the transcript.")
    before_entries = transcript_entries[:split_index]
    after_entries = transcript_entries[split_index:]
    if summarize_before:
        promoted_text = require_model_runner(runtime)(
            system_prompt=(
                "Summarize the provided transcript fragment for durable memory. "
                "Keep only what a later agent needs to continue from this point."
            ),
            transcript_text=serialize_context_entries(before_entries),
            model_override=model_override,
        )
    else:
        promoted_text = serialize_context_entries(before_entries)
    runtime.get_runtime_state().memory_field_rules.setdefault(target_field, "overwrite")
    overwrite_memory_value(runtime, field_name=target_field, value=promoted_text)
    apply_memory_refresh(runtime)
    refreshed_parameters, _ = split_context_window(current_context_window(runtime))
    return {"context_window": rebuild_context_window(refreshed_parameters, after_entries)}


def _coerce_indices(arguments: dict[str, Any], key: str) -> list[int]:
    raw = arguments.get(key)
    if not isinstance(raw, list) or not raw or not all(isinstance(item, int) and not isinstance(item, bool) for item in raw):
        raise ValueError(f"The '{key}' argument must be a non-empty array of integers.")
    return [int(item) for item in raw]


def _coerce_string_list(arguments: dict[str, Any], key: str) -> list[str]:
    raw = arguments.get(key)
    if not isinstance(raw, list) or not raw or not all(isinstance(item, str) for item in raw):
        raise ValueError(f"The '{key}' argument must be a non-empty array of strings.")
    return [str(item) for item in raw]


__all__ = [
    "annotate_entry",
    "checkpoint",
    "extract_and_collapse",
    "filter_by_tool_key",
    "keep_by_tag",
    "promote_and_strip",
    "split_and_promote",
]
