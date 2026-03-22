"""Group 5 transcript injection tools."""

from __future__ import annotations

from typing import Any

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

from . import (
    ContextToolRuntime,
    build_tool_definition,
    coerce_bool,
    coerce_int,
    coerce_optional_string,
    coerce_string,
    copy_entry,
    current_context_window,
    rebuild_context_window,
    split_context_window,
)


def create_context_injection_tools(runtime: ContextToolRuntime) -> tuple[RegisteredTool, ...]:
    return (
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_INJECT_SYNTHETIC_TOOL_RESULT,
                name="synthetic_tool_result",
                description="Inject a synthetic tool-result entry into the transcript.",
                properties={
                    "tool_key": {"type": "string"},
                    "output": {},
                    "label": {"type": "string"},
                },
                required=("tool_key", "output"),
            ),
            handler=lambda arguments: _synthetic_tool_result(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_INJECT_ASSISTANT_NOTE,
                name="assistant_note",
                description="Inject a synthetic assistant note into the transcript.",
                properties={
                    "content": {"type": "string"},
                    "note_type": {
                        "type": "string",
                        "enum": ["conclusion", "plan", "decision", "constraint", "observation"],
                    },
                },
                required=("content", "note_type"),
            ),
            handler=lambda arguments: _assistant_note(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_INJECT_TOOL_CALL_PAIR,
                name="tool_call_pair",
                description="Inject a synthetic tool-call/result pair into the transcript.",
                properties={
                    "tool_key": {"type": "string"},
                    "arguments": {"type": "object"},
                    "output": {},
                    "label": {"type": "string"},
                },
                required=("tool_key", "arguments", "output"),
            ),
            handler=lambda arguments: _tool_call_pair(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_INJECT_CONTEXT_BLOCK,
                name="context_block",
                description="Inject a labeled free-form context block into the transcript.",
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
            handler=lambda arguments: _context_block(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_INJECT_TASK_REMINDER,
                name="task_reminder",
                description="Inject a reminder of the task objective and continuation state.",
                properties={
                    "include_open_questions": {"type": "boolean"},
                    "include_verified_outputs_count": {"type": "boolean"},
                },
            ),
            handler=lambda arguments: _task_reminder(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_INJECT_REPLAY_MEMORY,
                name="replay_memory",
                description="Inject selected memory fields into the transcript as a synthetic tool result.",
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
            handler=lambda arguments: _replay_memory(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_INJECT_HANDOFF_BRIEF,
                name="handoff_brief",
                description="Inject a structured post-reset handoff brief into the transcript.",
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
            handler=lambda arguments: _handoff_brief(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_INJECT_PROGRESS_MARKER,
                name="progress_marker",
                description="Inject a lightweight milestone marker into the transcript.",
                properties={
                    "milestone_name": {"type": "string"},
                    "notes": {"type": "string"},
                },
                required=("milestone_name",),
            ),
            handler=lambda arguments: _progress_marker(runtime, arguments),
        ),
    )


def _synthetic_tool_result(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    tool_key = coerce_string(arguments, "tool_key")
    label = coerce_optional_string(arguments, "label")
    entry = {
        "kind": "tool_result",
        "tool_key": tool_key,
        "output": arguments["output"],
        "metadata": {"synthetic": True, "label": label},
    }
    return {"context_window": _append_transcript_entry(runtime, entry)}


def _assistant_note(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    content = coerce_string(arguments, "content")
    note_type = arguments.get("note_type")
    if note_type not in {"conclusion", "plan", "decision", "constraint", "observation"}:
        raise ValueError("The 'note_type' argument must be one of: conclusion, plan, decision, constraint, observation.")
    entry = {
        "kind": "assistant",
        "content": f"[{str(note_type).upper()}] {content}",
        "metadata": {"note_type": note_type, "synthetic": True},
    }
    return {"context_window": _append_transcript_entry(runtime, entry)}


def _tool_call_pair(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    tool_key = coerce_string(arguments, "tool_key")
    raw_arguments = arguments.get("arguments")
    if not isinstance(raw_arguments, dict):
        raise ValueError("The 'arguments' argument must be an object.")
    label = coerce_optional_string(arguments, "label")
    call_entry = {
        "kind": "tool_call",
        "tool_key": tool_key,
        "arguments": dict(raw_arguments),
        "metadata": {"label": label, "synthetic": True},
    }
    result_entry = {
        "kind": "tool_result",
        "tool_key": tool_key,
        "output": arguments["output"],
        "metadata": {"label": label, "synthetic": True},
    }
    return {"context_window": _append_transcript_entries(runtime, [call_entry, result_entry])}


def _context_block(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    label = coerce_string(arguments, "label")
    content = coerce_string(arguments, "content")
    position = arguments.get("position")
    if position not in {"current", "first", "last", "after_index"}:
        raise ValueError("The 'position' argument must be one of: current, first, last, after_index.")
    after_index = arguments.get("after_index")
    if position == "after_index":
        if isinstance(after_index, bool) or not isinstance(after_index, int):
            raise ValueError("The 'after_index' argument is required when position='after_index'.")
    entry = {"kind": "context", "label": label, "content": content}
    return {"context_window": _insert_transcript_entry(runtime, entry, position=position, after_index=after_index)}


def _task_reminder(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    include_open_questions = coerce_bool(arguments, "include_open_questions", default=False)
    include_verified_outputs_count = coerce_bool(arguments, "include_verified_outputs_count", default=True)
    state = runtime.get_runtime_state()
    objective = _original_objective(runtime)
    continuation_pointer = state.memory_fields.get("continuation_pointer")
    lines = [
        f"Objective: {objective}",
        f"Continuation pointer: {continuation_pointer if continuation_pointer is not None else '(not set)'}",
        f"Reset count: {runtime.get_reset_count()}",
    ]
    if include_verified_outputs_count:
        verified_outputs = state.memory_fields.get("verified_outputs", [])
        count = len(verified_outputs) if isinstance(verified_outputs, list) else 0
        lines.append(f"Verified outputs count: {count}")
    if include_open_questions and "open_questions" in state.memory_fields:
        lines.append(f"Open questions: {state.memory_fields.get('open_questions')}")
    entry = {
        "kind": "context",
        "label": "TASK REMINDER",
        "content": "\n".join(lines),
    }
    return {"context_window": _append_transcript_entry(runtime, entry)}


def _replay_memory(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    field_names = _coerce_string_list(arguments, "field_names")
    label = arguments.get("label", "MEMORY REPLAY")
    if not isinstance(label, str):
        raise ValueError("The 'label' argument must be a string when provided.")
    state = runtime.get_runtime_state()
    payload = {field_name: state.memory_fields.get(field_name) for field_name in field_names}
    entry = {
        "kind": "tool_result",
        "tool_key": "context.memory_replay",
        "output": payload,
        "metadata": {"label": label, "synthetic": True},
    }
    return {"context_window": _append_transcript_entry(runtime, entry)}


def _handoff_brief(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    raw_sections = arguments.get("include_sections")
    include_sections = (
        [str(item) for item in raw_sections]
        if isinstance(raw_sections, list) and all(isinstance(item, str) for item in raw_sections)
        else [
            "objective",
            "continuation_pointer",
            "completed_steps",
            "verified_outputs",
            "active_directives",
            "open_questions",
            "reset_history",
        ]
    )
    state = runtime.get_runtime_state()
    sections: list[str] = []
    if "objective" in include_sections:
        sections.append(f"Objective: {_original_objective(runtime)}")
    if "continuation_pointer" in include_sections:
        sections.append(f"Continuation Pointer: {state.memory_fields.get('continuation_pointer', '(not set)')}")
    if "completed_steps" in include_sections:
        sections.append(f"Completed Steps: {state.memory_fields.get('completed_steps', [])}")
    if "verified_outputs" in include_sections:
        verified = state.memory_fields.get("verified_outputs", [])
        count = len(verified) if isinstance(verified, list) else 0
        sections.append(f"Verified Outputs Count: {count}")
    if "active_directives" in include_sections:
        sections.append(f"Active Directives: {[directive.directive for directive in state.active_directives(runtime.get_reset_count())]}")
    if "open_questions" in include_sections:
        sections.append(f"Open Questions: {state.memory_fields.get('open_questions', [])}")
    if "reset_history" in include_sections:
        sections.append(f"Reset History: {state.memory_fields.get('reset_history', [])}")
    entry = {
        "kind": "context",
        "label": "HANDOFF BRIEF",
        "content": "\n".join(sections),
    }
    return {"context_window": _append_transcript_entry(runtime, entry)}


def _progress_marker(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    milestone_name = coerce_string(arguments, "milestone_name")
    notes = coerce_optional_string(arguments, "notes")
    content = f"[Reset {runtime.get_reset_count()} | Cycle {runtime.get_cycle_index()}] {milestone_name}"
    if notes:
        content = f"{content} — {notes}"
    entry = {"kind": "context", "label": "MILESTONE", "content": content}
    return {"context_window": _append_transcript_entry(runtime, entry)}


def _append_transcript_entry(runtime: ContextToolRuntime, entry: dict[str, Any]) -> list[dict[str, Any]]:
    return _append_transcript_entries(runtime, [entry])


def _append_transcript_entries(runtime: ContextToolRuntime, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    parameter_entries, transcript_entries = split_context_window(current_context_window(runtime))
    return rebuild_context_window(parameter_entries, [*map(copy_entry, transcript_entries), *entries])


def _insert_transcript_entry(
    runtime: ContextToolRuntime,
    entry: dict[str, Any],
    *,
    position: str,
    after_index: int | None,
) -> list[dict[str, Any]]:
    parameter_entries, transcript_entries = split_context_window(current_context_window(runtime))
    rewritten = [copy_entry(item) for item in transcript_entries]
    if position in {"current", "last"}:
        rewritten.append(entry)
    elif position == "first":
        rewritten.insert(0, entry)
    else:
        assert after_index is not None
        if after_index < 0 or after_index >= len(rewritten):
            raise ValueError("The 'after_index' argument is outside the transcript.")
        rewritten.insert(after_index + 1, entry)
    return rebuild_context_window(parameter_entries, rewritten)


def _original_objective(runtime: ContextToolRuntime) -> str:
    state = runtime.get_runtime_state()
    objective = state.memory_fields.get("original_objective")
    if objective is not None:
        return str(objective)
    if runtime.get_system_prompt is not None:
        prompt = runtime.get_system_prompt().strip()
        if prompt:
            return prompt.splitlines()[0]
    return "(objective unavailable)"


def _coerce_string_list(arguments: dict[str, Any], key: str) -> list[str]:
    raw = arguments.get(key)
    if not isinstance(raw, list) or not raw or not all(isinstance(item, str) for item in raw):
        raise ValueError(f"The '{key}' argument must be a non-empty array of strings.")
    return [str(item) for item in raw]


__all__ = ["create_context_injection_tools"]
