"""Group 1 context summarization tools."""

from __future__ import annotations

from typing import Any, Callable

from harnessiq.shared.tools import (
    CONTEXT_SUMMARIZE_CHRONOLOGICAL,
    CONTEXT_SUMMARIZE_DECISIONS,
    CONTEXT_SUMMARIZE_ENTITIES,
    CONTEXT_SUMMARIZE_ERRORS,
    CONTEXT_SUMMARIZE_EXTRACTED_DATA,
    CONTEXT_SUMMARIZE_GOALS_AND_GAPS,
    CONTEXT_SUMMARIZE_HEADLINE,
    CONTEXT_SUMMARIZE_OPEN_QUESTIONS,
    CONTEXT_SUMMARIZE_STATE_SNAPSHOT,
    RegisteredTool,
)

from . import (
    ContextToolRuntime,
    build_tool_definition,
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


def create_context_summarization_tools(runtime: ContextToolRuntime) -> tuple[RegisteredTool, ...]:
    return (
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_SUMMARIZE_HEADLINE,
                name="headline",
                description="Compress the transcript into a short executive summary.",
                properties={"model_override": {"type": "string"}},
            ),
            handler=lambda arguments: _summarize(
                runtime,
                tool_key=CONTEXT_SUMMARIZE_HEADLINE,
                output_key="summary",
                system_prompt=_headline_prompt(arguments),
                model_override=coerce_optional_string(arguments, "model_override"),
            ),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_SUMMARIZE_CHRONOLOGICAL,
                name="chronological",
                description="Compress the transcript into a strict chronological narrative.",
                properties={
                    "include_tool_outputs": {"type": "boolean"},
                    "model_override": {"type": "string"},
                },
            ),
            handler=lambda arguments: _summarize(
                runtime,
                tool_key=CONTEXT_SUMMARIZE_CHRONOLOGICAL,
                output_key="summary",
                system_prompt=_chronological_prompt(arguments),
                model_override=coerce_optional_string(arguments, "model_override"),
            ),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_SUMMARIZE_STATE_SNAPSHOT,
                name="state_snapshot",
                description="Compress the transcript into a current-world-state snapshot.",
                properties={
                    "entity_types": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "model_override": {"type": "string"},
                },
            ),
            handler=lambda arguments: _summarize(
                runtime,
                tool_key=CONTEXT_SUMMARIZE_STATE_SNAPSHOT,
                output_key="snapshot",
                system_prompt=_state_snapshot_prompt(arguments),
                model_override=coerce_optional_string(arguments, "model_override"),
            ),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_SUMMARIZE_DECISIONS,
                name="decisions",
                description="Extract only decision points and their rationale.",
                properties={
                    "include_implicit_decisions": {"type": "boolean"},
                    "model_override": {"type": "string"},
                },
            ),
            handler=lambda arguments: _summarize(
                runtime,
                tool_key=CONTEXT_SUMMARIZE_DECISIONS,
                output_key="decisions",
                system_prompt=_decisions_prompt(arguments),
                model_override=coerce_optional_string(arguments, "model_override"),
            ),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_SUMMARIZE_ERRORS,
                name="errors",
                description="Extract only failures, unexpected outputs, and pivots.",
                properties={
                    "include_warnings": {"type": "boolean"},
                    "model_override": {"type": "string"},
                },
            ),
            handler=lambda arguments: _summarize(
                runtime,
                tool_key=CONTEXT_SUMMARIZE_ERRORS,
                output_key="errors",
                system_prompt=_errors_prompt(arguments),
                model_override=coerce_optional_string(arguments, "model_override"),
            ),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_SUMMARIZE_EXTRACTED_DATA,
                name="extracted_data",
                description="Extract only discovered facts and data points.",
                properties={
                    "min_confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                    },
                    "model_override": {"type": "string"},
                },
            ),
            handler=lambda arguments: _summarize(
                runtime,
                tool_key=CONTEXT_SUMMARIZE_EXTRACTED_DATA,
                output_key="facts",
                system_prompt=_extracted_data_prompt(arguments),
                model_override=coerce_optional_string(arguments, "model_override"),
            ),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_SUMMARIZE_GOALS_AND_GAPS,
                name="goals_and_gaps",
                description="Compare progress against the top-level objective.",
                properties={
                    "objective_override": {"type": "string"},
                    "model_override": {"type": "string"},
                },
            ),
            handler=lambda arguments: _summarize(
                runtime,
                tool_key=CONTEXT_SUMMARIZE_GOALS_AND_GAPS,
                output_key="assessment",
                system_prompt=_goals_and_gaps_prompt(runtime, arguments),
                model_override=coerce_optional_string(arguments, "model_override"),
            ),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_SUMMARIZE_ENTITIES,
                name="entities",
                description="Build an entity-centric registry from the transcript.",
                properties={
                    "entity_filter": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "model_override": {"type": "string"},
                },
            ),
            handler=lambda arguments: _summarize(
                runtime,
                tool_key=CONTEXT_SUMMARIZE_ENTITIES,
                output_key="entities",
                system_prompt=_entities_prompt(arguments),
                model_override=coerce_optional_string(arguments, "model_override"),
            ),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_SUMMARIZE_OPEN_QUESTIONS,
                name="open_questions",
                description="Extract unresolved questions and ambiguities.",
                properties={
                    "include_resolved": {"type": "boolean"},
                    "model_override": {"type": "string"},
                },
            ),
            handler=lambda arguments: _summarize(
                runtime,
                tool_key=CONTEXT_SUMMARIZE_OPEN_QUESTIONS,
                output_key="open_questions",
                system_prompt=_open_questions_prompt(arguments),
                model_override=coerce_optional_string(arguments, "model_override"),
            ),
        ),
    )


def _summarize(
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


def _headline_prompt(arguments: dict[str, Any]) -> str:
    del arguments
    return (
        "Ignore all tool call details, intermediate steps, and reasoning traces. "
        "Read the conversation and answer two questions in plain prose: "
        "(1) What has been completed so far? (2) What is the current active objective? "
        "Your response must be 3 to 5 sentences. Do not reference specific tool names or output values."
    )


def _chronological_prompt(arguments: dict[str, Any]) -> str:
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


def _state_snapshot_prompt(arguments: dict[str, Any]) -> str:
    entity_types = coerce_string_list(arguments, "entity_types")
    prompt = (
        "Ignore the sequence of events entirely. Read the conversation and produce a structured "
        "snapshot of the current state of the world. For each entity, resource, or record mentioned: "
        "state its name, its current known value or status, and whether it was modified during this session. "
        "Output as a structured list of `entity: status` pairs. Do not describe what happened — describe what is."
    )
    if entity_types:
        prompt += f" Only include the following entity categories: {', '.join(entity_types)}."
    return prompt


def _decisions_prompt(arguments: dict[str, Any]) -> str:
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


def _errors_prompt(arguments: dict[str, Any]) -> str:
    include_warnings = coerce_bool(arguments, "include_warnings", default=False)
    prompt = (
        "Read the conversation and extract every failure: tool errors, unexpected outputs, abandoned approaches, "
        "and the pivot or retry that followed each one. For each: state what failed, what the error or unexpected "
        "output was, and what the agent did next. Ignore all successful steps. Output as a numbered list."
    )
    if include_warnings:
        prompt += " Include warning-level outputs that materially influenced the next action."
    return prompt


def _extracted_data_prompt(arguments: dict[str, Any]) -> str:
    min_confidence = arguments.get("min_confidence", "low")
    if min_confidence not in {"high", "medium", "low"}:
        raise ValueError("The 'min_confidence' argument must be one of: high, medium, low.")
    return (
        "Read the conversation and extract every factual claim that was returned by a tool or established during execution. "
        "For each fact: state the fact, note its source tool key, and rate your confidence as high/medium/low. "
        f"Only include facts at confidence {min_confidence} or higher. "
        "Ignore all process steps, decisions, and reasoning. Output as a numbered list of `[source] fact (confidence)` entries."
    )


def _goals_and_gaps_prompt(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> str:
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
        "Be specific — reference the original objective's exact requirements."
    )
    if objective:
        prompt += f" Use this explicit objective text instead of inferring it: {objective}"
    return prompt


def _entities_prompt(arguments: dict[str, Any]) -> str:
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


def _open_questions_prompt(arguments: dict[str, Any]) -> str:
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


__all__ = ["create_context_summarization_tools"]
