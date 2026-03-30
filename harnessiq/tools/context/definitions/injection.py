"""
===============================================================================
File: harnessiq/tools/context/definitions/injection.py

What this file does:
- Implements part of the context-tool system that rewrites, summarizes, or
  annotates an agent context window.
- Tool definitions for transcript injection context tools.

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
    CONTEXT_INJECT_ASSISTANT_NOTE,
    CONTEXT_INJECT_CONTEXT_BLOCK,
    CONTEXT_INJECT_HANDOFF_BRIEF,
    CONTEXT_INJECT_PROGRESS_MARKER,
    CONTEXT_INJECT_REPLAY_MEMORY,
    CONTEXT_INJECT_SYNTHETIC_TOOL_RESULT,
    CONTEXT_INJECT_TASK_REMINDER,
    CONTEXT_INJECT_TOOL_CALL_PAIR,
    RegisteredTool,
)

from .. import ContextToolRuntime, build_tool_definition
from ..executors.injection import (
    assistant_note,
    context_block,
    handoff_brief,
    progress_marker,
    replay_memory,
    synthetic_tool_result,
    task_reminder,
    tool_call_pair,
)


def create_context_injection_tools(runtime: ContextToolRuntime) -> tuple[RegisteredTool, ...]:
    return (
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_INJECT_SYNTHETIC_TOOL_RESULT,
                name="synthetic_tool_result",
                description=(
                    "Insert a synthetic tool-result entry into the transcript without rerunning a tool. "
                    "Use it when the agent needs to preserve a tool-shaped artifact, replay an already known result, "
                    "or restate structured output from outside the live tool loop. "
                    "The inserted entry is marked synthetic so later inspection can distinguish it from real execution."
                ),
                properties={
                    "tool_key": {"type": "string"},
                    "output": {},
                    "label": {"type": "string"},
                },
                required=("tool_key", "output"),
            ),
            handler=lambda arguments: synthetic_tool_result(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_INJECT_ASSISTANT_NOTE,
                name="assistant_note",
                description=(
                    "Insert a synthetic assistant message into the transcript. "
                    "Use this to pin a conclusion, plan, decision, constraint, or observation into the visible context "
                    "without waiting for another model turn to restate it. "
                    "The note is tagged with a note type so later tooling can treat it as deliberate scaffolding instead of a live response."
                ),
                properties={
                    "content": {"type": "string"},
                    "note_type": {
                        "type": "string",
                        "enum": ["conclusion", "plan", "decision", "constraint", "observation"],
                    },
                },
                required=("content", "note_type"),
            ),
            handler=lambda arguments: assistant_note(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_INJECT_TOOL_CALL_PAIR,
                name="tool_call_pair",
                description=(
                    "Insert a synthetic tool-call and tool-result pair as if the action had already been executed. "
                    "This is useful for replaying prior work, preserving externally obtained results, or restoring execution context "
                    "after a reset without invoking the underlying tool again. "
                    "Both inserted entries are marked synthetic so the transcript still preserves provenance."
                ),
                properties={
                    "tool_key": {"type": "string"},
                    "arguments": {"type": "object"},
                    "output": {},
                    "label": {"type": "string"},
                },
                required=("tool_key", "arguments", "output"),
            ),
            handler=lambda arguments: tool_call_pair(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_INJECT_CONTEXT_BLOCK,
                name="context_block",
                description=(
                    "Insert a labeled free-form context block into the transcript. "
                    "Use it to preserve structured notes, operator guidance, or synthetic state markers that do not fit naturally "
                    "as assistant text or tool output. "
                    "The position controls whether the block is appended, prepended, or inserted after a specific transcript index."
                ),
                properties={
                    "label": {"type": "string"},
                    "content": {"type": "string"},
                    "position": {
                        "type": "string",
                        "enum": ["current", "first", "last", "after_index"],
                    },
                    "after_index": {"type": "integer"},
                },
                required=("label", "content", "position"),
            ),
            handler=lambda arguments: context_block(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_INJECT_TASK_REMINDER,
                name="task_reminder",
                description=(
                    "Inject a synthesized reminder of the active objective and progress signals. "
                    "This gives the agent a compact orientation block that restates the continuation pointer, reset count, "
                    "and optionally verified outputs or open questions. "
                    "Use it when the transcript has drifted and the model needs the current mission restated near the working set."
                ),
                properties={
                    "include_open_questions": {"type": "boolean"},
                    "include_verified_outputs_count": {"type": "boolean"},
                },
            ),
            handler=lambda arguments: task_reminder(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_INJECT_REPLAY_MEMORY,
                name="replay_memory",
                description=(
                    "Inject selected durable memory fields back into the transcript as a synthetic tool result. "
                    "This is useful when the agent needs previously persisted state to become visible inside the active transcript "
                    "without mutating the underlying memory fields themselves. "
                    "The replayed payload stays clearly marked as synthetic so later steps can trace where it came from."
                ),
                properties={
                    "field_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                    },
                    "label": {"type": "string"},
                },
                required=("field_names",),
            ),
            handler=lambda arguments: replay_memory(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_INJECT_HANDOFF_BRIEF,
                name="handoff_brief",
                description=(
                    "Inject a structured post-reset handoff brief into the transcript. "
                    "The brief can restate the objective, continuation pointer, completed steps, verified outputs, directives, "
                    "open questions, and reset history so a later turn can resume quickly. "
                    "Use it as a deliberate orientation artifact when the agent needs to rehydrate itself after compaction or reset."
                ),
                properties={
                    "include_sections": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "objective",
                                "continuation_pointer",
                                "completed_steps",
                                "verified_outputs",
                                "active_directives",
                                "open_questions",
                                "reset_history",
                            ],
                        },
                    }
                },
            ),
            handler=lambda arguments: handoff_brief(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_INJECT_PROGRESS_MARKER,
                name="progress_marker",
                description=(
                    "Inject a lightweight milestone marker into the transcript. "
                    "This creates a compact breadcrumb that records which reset and cycle reached a named milestone, "
                    "optionally with a short note about what changed. "
                    "Use it to make later compaction, debugging, or recovery passes easier to interpret."
                ),
                properties={
                    "milestone_name": {"type": "string"},
                    "notes": {"type": "string"},
                },
                required=("milestone_name",),
            ),
            handler=lambda arguments: progress_marker(runtime, arguments),
        ),
    )


__all__ = ["create_context_injection_tools"]
