"""
===============================================================================
File: harnessiq/tools/context/definitions/catalog.py

What this file does:
- Implements part of the context-tool system that rewrites, summarizes, or
  annotates an agent context window.
- Tool definitions for additional catalog context tools.

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
    CONTEXT_ANNOTATE_PHASE,
    CONTEXT_COLLAPSE_REPEATED_CALLS,
    CONTEXT_ESTIMATE_WINDOW_PRESSURE,
    CONTEXT_HANDOFF_BRIEF,
    CONTEXT_INJECT_REMINDER,
    CONTEXT_PRUNE_TOOL_RESULTS,
    CONTEXT_SUMMARIZE_TRANSCRIPT,
    CONTEXT_TRIM_OLDEST_ENTRIES,
    RegisteredTool,
)

from .. import ContextToolRuntime, build_tool_definition
from ..executors.catalog import (
    annotate_phase,
    collapse_repeated_calls,
    estimate_window_pressure,
    handoff_brief,
    inject_reminder,
    prune_tool_results,
    summarize_transcript,
    trim_oldest_entries,
)


def create_context_catalog_tools(runtime: ContextToolRuntime) -> tuple[RegisteredTool, ...]:
    return (
        RegisteredTool(build_tool_definition(key=CONTEXT_SUMMARIZE_TRANSCRIPT, name="summarize_transcript", description="Produce a structured transcript handoff summary.", properties={"detail_level": {"type": "string", "enum": ["minimal", "standard", "full"]}, "max_output_tokens": {"type": "integer"}, "focus_fields": {"type": "array", "items": {"type": "string"}}}), lambda arguments: summarize_transcript(runtime, arguments)),
        RegisteredTool(build_tool_definition(key=CONTEXT_PRUNE_TOOL_RESULTS, name="prune_tool_results", description="Prune older tool-result bodies while preserving call metadata.", properties={"keep_last_n": {"type": "integer", "minimum": 0}, "tool_filter": {"type": "array", "items": {"type": "string"}}, "replacement_text": {"type": "string"}}), lambda arguments: prune_tool_results(runtime, arguments)),
        RegisteredTool(build_tool_definition(key=CONTEXT_ESTIMATE_WINDOW_PRESSURE, name="estimate_window_pressure", description="Estimate current context-window pressure and reset risk.", properties={"planned_action_tokens": {"type": ["integer", "null"]}, "reset_token_limit": {"type": ["integer", "null"]}}), lambda arguments: estimate_window_pressure(runtime, arguments)),
        RegisteredTool(build_tool_definition(key=CONTEXT_TRIM_OLDEST_ENTRIES, name="trim_oldest_entries", description="Trim the oldest transcript entries with an optional summary marker.", properties={"n": {"type": "integer", "minimum": 0}, "min_preserve": {"type": "integer", "minimum": 0}, "summarize_dropped": {"type": "boolean"}}, required=("n",)), lambda arguments: trim_oldest_entries(runtime, arguments)),
        RegisteredTool(build_tool_definition(key=CONTEXT_HANDOFF_BRIEF, name="handoff_brief", description="Compose a structured handoff brief payload for durable memory.", properties={"continuation_pointer": {"type": "string"}, "task_goal": {"type": "string"}, "completed_outputs": {"type": "array", "items": {"type": "object"}}, "active_constraints": {"type": "array", "items": {"type": "string"}}, "blockers": {"type": "array", "items": {"type": "object"}}, "recent_decisions": {"type": "array", "items": {"type": "object"}}, "schema_version": {"type": "string"}}, required=("continuation_pointer", "task_goal")), lambda arguments: handoff_brief(runtime, arguments)),
        RegisteredTool(build_tool_definition(key=CONTEXT_COLLAPSE_REPEATED_CALLS, name="collapse_repeated_calls", description="Collapse identical repeated tool-call runs into one representative entry.", properties={"min_repetitions": {"type": "integer", "minimum": 0}, "tool_filter": {"type": "array", "items": {"type": "string"}}, "collapse_near_identical": {"type": "boolean"}}), lambda arguments: collapse_repeated_calls(runtime, arguments)),
        RegisteredTool(build_tool_definition(key=CONTEXT_ANNOTATE_PHASE, name="annotate_phase", description="Insert a transcript phase marker for task navigation.", properties={"phase_name": {"type": "string"}, "description": {"type": "string"}, "phase_number": {"type": ["integer", "null"]}}, required=("phase_name",)), lambda arguments: annotate_phase(runtime, arguments)),
        RegisteredTool(build_tool_definition(key=CONTEXT_INJECT_REMINDER, name="inject_reminder", description="Inject a synthetic reminder message into the transcript.", properties={"content": {"type": "string"}, "label": {"type": "string"}, "format": {"type": "string", "enum": ["plaintext", "markdown"]}}, required=("content",)), lambda arguments: inject_reminder(runtime, arguments)),
    )


__all__ = ["create_context_catalog_tools"]
