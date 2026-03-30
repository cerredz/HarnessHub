"""
===============================================================================
File: harnessiq/tools/context/executors/summarization.py

What this file does:
- Implements part of the context-tool system that rewrites, summarizes, or
  annotates an agent context window.
- Execution logic for context summarization tools.

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

from typing import Any

from .. import (
    ContextToolRuntime,
    coerce_bool,
    coerce_optional_string,
    coerce_string_list,
    context_window_tokens,
    current_context_window,
    rebuild_context_window,
    require_model_runner,
    serialize_context_entries,
    split_context_window,
)


def summarize(
    runtime: ContextToolRuntime,
    *,
    tool_key: str,
    output_key: str,
    system_prompt: str,
    model_override: str | None,
) -> dict[str, Any]:
    context_window = current_context_window(runtime)
    parameter_entries, transcript_entries = split_context_window(context_window)
    transcript_text = serialize_context_entries(transcript_entries)
    summary_text = require_model_runner(runtime)(
        system_prompt=system_prompt,
        transcript_text=transcript_text,
        model_override=model_override,
    )
    output = {
        output_key: summary_text,
        "tokens_after": context_window_tokens([{"kind": "summary", "content": summary_text}]),
        "tokens_before": context_window_tokens(transcript_entries),
    }
    result_entry = {
        "kind": "tool_result",
        "tool_key": tool_key,
        "output": output,
    }
    return {"context_window": rebuild_context_window(parameter_entries, [result_entry])}


def headline_prompt(arguments: dict[str, Any]) -> str:
    del arguments
    return (
        "Ignore all tool call details, intermediate steps, and reasoning traces. "
        "Read the conversation and answer two questions in plain prose: "
        "(1) What has been completed so far? (2) What is the current active objective? "
        "Your response must be 3 to 5 sentences. Do not reference specific tool names or output values."
    )


def chronological_prompt(arguments: dict[str, Any]) -> str:
    include_tool_outputs = coerce_bool(arguments, "include_tool_outputs", default=False)
    prompt = (
        "Read the conversation and produce a chronological narrative. For each step: "
        "describe what the agent attempted, summarize the tool result in one sentence, and "
        "state what decision or action followed. Write in past tense. Preserve sequence strictly "
        "and focus on decisions and results, not internal reasoning."
    )
    if include_tool_outputs:
        prompt += " Include verbatim short tool outputs when they are under 50 tokens."
    return prompt


def state_snapshot_prompt(arguments: dict[str, Any]) -> str:
    entity_types = coerce_string_list(arguments, "entity_types")
    prompt = (
        "Ignore the sequence of events entirely. Read the conversation and produce a structured "
        "snapshot of the current state of the world. For each entity, resource, or record mentioned: "
        "state its name, its current known value or status, and whether it was modified during this session. "
        "Output as a structured list of `entity: status` pairs. Do not describe what happened - describe what is."
    )
    if entity_types:
        prompt += f" Only include the following entity categories: {', '.join(entity_types)}."
    return prompt


def decisions_prompt(arguments: dict[str, Any]) -> str:
    include_implicit = coerce_bool(arguments, "include_implicit_decisions", default=True)
    prompt = (
        "Read the conversation and extract every decision point: moments where the agent evaluated options "
        "and chose one. For each: state the decision made, list the alternatives that were visible or considered, "
        "and give the stated or implied reason for the choice. Ignore steps that had no alternatives. "
        "Output as a numbered list."
    )
    if not include_implicit:
        prompt += " Only include decisions where the alternatives were explicitly stated."
    return prompt


def errors_prompt(arguments: dict[str, Any]) -> str:
    include_warnings = coerce_bool(arguments, "include_warnings", default=False)
    prompt = (
        "Read the conversation and extract every failure: tool errors, unexpected outputs, abandoned approaches, "
        "and the pivot or retry that followed each one. For each: state what failed, what the error or unexpected "
        "output was, and what the agent did next. Ignore all successful steps. Output as a numbered list."
    )
    if include_warnings:
        prompt += " Include warning-level outputs that materially influenced the next action."
    return prompt


def extracted_data_prompt(arguments: dict[str, Any]) -> str:
    min_confidence = arguments.get("min_confidence", "low")
    if min_confidence not in {"high", "medium", "low"}:
        raise ValueError("The 'min_confidence' argument must be one of: high, medium, low.")
    return (
        "Read the conversation and extract every factual claim that was returned by a tool or established during execution. "
        "For each fact: state the fact, note its source tool key, and rate your confidence as high/medium/low. "
        f"Only include facts at confidence {min_confidence} or higher. "
        "Ignore all process steps, decisions, and reasoning. Output as a numbered list of `[source] fact (confidence)` entries."
    )


def goals_and_gaps_prompt(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> str:
    objective_override = coerce_optional_string(arguments, "objective_override")
    objective = objective_override
    if objective is None:
        state = runtime.get_runtime_state()
        raw_objective = state.memory_fields.get("original_objective")
        objective = str(raw_objective) if raw_objective is not None else None
    prompt = (
        "Read the conversation. The first user message states the original task objective. "
        "For everything that has happened since: identify which parts of the original objective have been fully satisfied, "
        "which are partially satisfied, and which have not yet been addressed. Output two structured lists: COMPLETED and REMAINING. "
        "Be specific - reference the original objective's exact requirements."
    )
    if objective:
        prompt += f" Use this explicit objective text instead of inferring it: {objective}"
    return prompt


def entities_prompt(arguments: dict[str, Any]) -> str:
    entity_filter = coerce_string_list(arguments, "entity_filter")
    prompt = (
        "Read the conversation and produce an entity registry. For each named entity encountered "
        "(person, file path, URL, ID, record, account, or other discrete object): state the entity's "
        "name or identifier, classify its type, and describe its last-known status or value. Group entries "
        "by entity type. Each entry should be one line."
    )
    if entity_filter:
        prompt += f" Only include these entity types when relevant: {', '.join(entity_filter)}."
    return prompt


def open_questions_prompt(arguments: dict[str, Any]) -> str:
    include_resolved = coerce_bool(arguments, "include_resolved", default=False)
    prompt = (
        "Read the conversation and extract every open question: moments where the agent encountered ambiguity, "
        "deferred a decision, stated an assumption without verifying it, or flagged that something was unclear. "
        "For each: state what is unresolved and what information or action would resolve it. Ignore everything "
        "that was conclusively answered or resolved. Output as a numbered list."
    )
    if include_resolved:
        prompt += " Append a brief note when a previously open question was later resolved."
    return prompt


__all__ = [
    "chronological_prompt",
    "decisions_prompt",
    "entities_prompt",
    "errors_prompt",
    "extracted_data_prompt",
    "goals_and_gaps_prompt",
    "headline_prompt",
    "open_questions_prompt",
    "state_snapshot_prompt",
    "summarize",
]
