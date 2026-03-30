"""
===============================================================================
File: harnessiq/tools/context/definitions/summarization.py

What this file does:
- Implements part of the context-tool system that rewrites, summarizes, or
  annotates an agent context window.
- Tool definitions for context summarization tools.

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

from .. import ContextToolRuntime, build_tool_definition, coerce_optional_string
from ..executors.summarization import (
    summarize,
    chronological_prompt,
    decisions_prompt,
    entities_prompt,
    errors_prompt,
    extracted_data_prompt,
    goals_and_gaps_prompt,
    headline_prompt,
    open_questions_prompt,
    state_snapshot_prompt,
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
            handler=lambda arguments: summarize(
                runtime,
                tool_key=CONTEXT_SUMMARIZE_HEADLINE,
                output_key="summary",
                system_prompt=headline_prompt(arguments),
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
            handler=lambda arguments: summarize(
                runtime,
                tool_key=CONTEXT_SUMMARIZE_CHRONOLOGICAL,
                output_key="summary",
                system_prompt=chronological_prompt(arguments),
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
            handler=lambda arguments: summarize(
                runtime,
                tool_key=CONTEXT_SUMMARIZE_STATE_SNAPSHOT,
                output_key="snapshot",
                system_prompt=state_snapshot_prompt(arguments),
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
            handler=lambda arguments: summarize(
                runtime,
                tool_key=CONTEXT_SUMMARIZE_DECISIONS,
                output_key="decisions",
                system_prompt=decisions_prompt(arguments),
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
            handler=lambda arguments: summarize(
                runtime,
                tool_key=CONTEXT_SUMMARIZE_ERRORS,
                output_key="errors",
                system_prompt=errors_prompt(arguments),
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
            handler=lambda arguments: summarize(
                runtime,
                tool_key=CONTEXT_SUMMARIZE_EXTRACTED_DATA,
                output_key="facts",
                system_prompt=extracted_data_prompt(arguments),
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
            handler=lambda arguments: summarize(
                runtime,
                tool_key=CONTEXT_SUMMARIZE_GOALS_AND_GAPS,
                output_key="assessment",
                system_prompt=goals_and_gaps_prompt(runtime, arguments),
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
            handler=lambda arguments: summarize(
                runtime,
                tool_key=CONTEXT_SUMMARIZE_ENTITIES,
                output_key="entities",
                system_prompt=entities_prompt(arguments),
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
            handler=lambda arguments: summarize(
                runtime,
                tool_key=CONTEXT_SUMMARIZE_OPEN_QUESTIONS,
                output_key="open_questions",
                system_prompt=open_questions_prompt(arguments),
                model_override=coerce_optional_string(arguments, "model_override"),
            ),
        ),
    )


__all__ = ["create_context_summarization_tools"]
