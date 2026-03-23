"""Group 4 parameter-zone injection tools."""

from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import uuid4

from harnessiq.shared.agents import AgentContextDirective, AgentInjectedSection, estimate_text_tokens
from harnessiq.shared.tools import (
    CONTEXT_PARAM_APPEND_MEMORY_FIELD,
    CONTEXT_PARAM_BULK_WRITE_MEMORY,
    CONTEXT_PARAM_CLEAR_MEMORY_FIELD,
    CONTEXT_PARAM_INJECT_DIRECTIVE,
    CONTEXT_PARAM_INJECT_SECTION,
    CONTEXT_PARAM_OVERWRITE_MEMORY_FIELD,
    CONTEXT_PARAM_UPDATE_SECTION,
    CONTEXT_PARAM_WRITE_ONCE_MEMORY_FIELD,
    RegisteredTool,
)

from . import (
    ContextToolRuntime,
    apply_memory_refresh,
    build_tool_definition,
    coerce_bool,
    coerce_optional_string,
    coerce_string,
    current_context_window,
    split_context_window,
)

_UNSET = object()


def create_context_parameter_tools(runtime: ContextToolRuntime) -> tuple[RegisteredTool, ...]:
    return (
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_PARAM_INJECT_SECTION,
                name="inject_section",
                description="Create a new durable parameter section.",
                properties={
                    "section_label": {"type": "string"},
                    "content": {"type": "string"},
                    "position": {
                        "type": "string",
                        "enum": ["first", "last", "after_master_prompt", "before_memory"],
                    },
                },
                required=("section_label", "content", "position"),
            ),
            handler=lambda arguments: _inject_section(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_PARAM_UPDATE_SECTION,
                name="update_section",
                description="Replace the content of an existing durable parameter section.",
                properties={
                    "section_label": {"type": "string"},
                    "content": {"type": "string"},
                },
                required=("section_label", "content"),
            ),
            handler=lambda arguments: _update_section(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_PARAM_APPEND_MEMORY_FIELD,
                name="append_memory_field",
                description="Append a new value to a durable memory field.",
                properties={
                    "field_name": {"type": "string"},
                    "value": {},
                    "timestamp": {"type": "boolean"},
                },
                required=("field_name", "value"),
            ),
            handler=lambda arguments: _append_memory_field(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_PARAM_OVERWRITE_MEMORY_FIELD,
                name="overwrite_memory_field",
                description="Overwrite a durable memory field.",
                properties={
                    "field_name": {"type": "string"},
                    "value": {},
                    "previous_value_check": {},
                },
                required=("field_name", "value"),
            ),
            handler=lambda arguments: _overwrite_memory_field(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_PARAM_WRITE_ONCE_MEMORY_FIELD,
                name="write_once_memory_field",
                description="Write a durable memory field exactly once.",
                properties={
                    "field_name": {"type": "string"},
                    "value": {},
                },
                required=("field_name", "value"),
            ),
            handler=lambda arguments: _write_once_memory_field(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_PARAM_INJECT_DIRECTIVE,
                name="inject_directive",
                description="Append a durable directive to the effective system prompt.",
                properties={
                    "directive": {"type": "string"},
                    "priority": {
                        "type": "string",
                        "enum": ["critical", "standard", "advisory"],
                    },
                    "expires_after_resets": {"type": "integer"},
                },
                required=("directive", "priority"),
            ),
            handler=lambda arguments: _inject_directive(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_PARAM_CLEAR_MEMORY_FIELD,
                name="clear_memory_field",
                description="Clear a durable memory field with an explicit reason sentinel.",
                properties={
                    "field_name": {"type": "string"},
                    "reason": {"type": "string"},
                },
                required=("field_name", "reason"),
            ),
            handler=lambda arguments: _clear_memory_field(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_PARAM_BULK_WRITE_MEMORY,
                name="bulk_write_memory",
                description="Apply multiple durable memory writes atomically.",
                properties={
                    "writes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "field_name": {"type": "string"},
                                "value": {},
                                "update_rule": {
                                    "type": "string",
                                    "enum": ["overwrite", "append", "write_once"],
                                },
                            },
                            "required": ["field_name", "value", "update_rule"],
                            "additionalProperties": False,
                        },
                        "minItems": 1,
                    }
                },
                required=("writes",),
            ),
            handler=lambda arguments: _bulk_write_memory(runtime, arguments),
        ),
    )


def append_memory_value(
    runtime: ContextToolRuntime,
    *,
    field_name: str,
    value: Any,
    timestamp: bool = True,
) -> dict[str, Any]:
    state = runtime.get_runtime_state()
    state.memory_field_rules[field_name] = "append"
    current = state.memory_fields.get(field_name)
    if current is None:
        current_items: list[Any] = []
    elif isinstance(current, list):
        current_items = list(current)
    else:
        raise ValueError(f"Memory field '{field_name}' is not append-compatible.")
    rendered_value = _timestamped_value(runtime, value) if timestamp else deepcopy(value)
    current_items.append(rendered_value)
    state.memory_fields[field_name] = current_items
    return {
        "field_name": field_name,
        "appended_value": rendered_value,
        "field_length": len(current_items),
        "update_rule": "append",
    }


def overwrite_memory_value(
    runtime: ContextToolRuntime,
    *,
    field_name: str,
    value: Any,
    previous_value_check: Any = _UNSET,
) -> dict[str, Any]:
    state = runtime.get_runtime_state()
    if field_name not in state.memory_field_rules and field_name not in state.memory_fields:
        raise ValueError(f"Unknown memory field '{field_name}'.")
    rule = state.memory_field_rules.get(field_name, "overwrite")
    if rule != "overwrite":
        raise ValueError(f"Memory field '{field_name}' does not use the overwrite update rule.")
    previous_value = deepcopy(state.memory_fields.get(field_name))
    if previous_value_check is not _UNSET and previous_value != previous_value_check:
        raise ValueError(f"Memory field '{field_name}' did not match previous_value_check.")
    state.memory_field_rules[field_name] = "overwrite"
    state.memory_fields[field_name] = deepcopy(value)
    return {
        "field_name": field_name,
        "previous_value": previous_value,
        "new_value": deepcopy(value),
        "update_rule": "overwrite",
    }


def write_once_memory_value(
    runtime: ContextToolRuntime,
    *,
    field_name: str,
    value: Any,
) -> dict[str, Any]:
    state = runtime.get_runtime_state()
    existing = state.memory_fields.get(field_name)
    if existing is not None:
        return {
            "error": "FIELD_ALREADY_WRITTEN",
            "existing_value": deepcopy(existing),
            "field_name": field_name,
        }
    state.memory_field_rules[field_name] = "write_once"
    state.memory_fields[field_name] = deepcopy(value)
    return {
        "field_name": field_name,
        "new_value": deepcopy(value),
        "update_rule": "write_once",
    }


def _inject_section(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    section_label = coerce_string(arguments, "section_label")
    content = coerce_string(arguments, "content")
    position = arguments.get("position")
    if position not in {"first", "last", "after_master_prompt", "before_memory"}:
        raise ValueError("The 'position' argument must be one of: first, last, after_master_prompt, before_memory.")
    state = runtime.get_runtime_state()
    state.injected_sections = [
        section
        for section in state.injected_sections
        if section.label != section_label
    ]
    state.injected_sections.append(
        AgentInjectedSection(label=section_label, content=content, position=position)
    )
    apply_memory_refresh(runtime)
    return {
        "section_label": section_label,
        "position": position,
        "token_count": estimate_text_tokens(content),
        "total_parameter_tokens": _total_parameter_tokens(runtime),
    }


def _update_section(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    section_label = coerce_string(arguments, "section_label")
    content = coerce_string(arguments, "content")
    previous_content = _current_section_content(runtime, section_label)
    state = runtime.get_runtime_state()
    for index, section in enumerate(state.injected_sections):
        if section.label == section_label:
            state.injected_sections[index] = AgentInjectedSection(
                label=section.label,
                content=content,
                position=section.position,
            )
            break
    else:
        state.section_overrides[section_label] = content
    apply_memory_refresh(runtime)
    return {
        "section_label": section_label,
        "previous_token_count": estimate_text_tokens(previous_content or ""),
        "new_token_count": estimate_text_tokens(content),
    }


def _append_memory_field(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    field_name = coerce_string(arguments, "field_name")
    timestamp = coerce_bool(arguments, "timestamp", default=True)
    payload = append_memory_value(runtime, field_name=field_name, value=arguments["value"], timestamp=timestamp)
    apply_memory_refresh(runtime)
    return payload


def _overwrite_memory_field(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    field_name = coerce_string(arguments, "field_name")
    previous_value_check = arguments.get("previous_value_check", _UNSET)
    payload = overwrite_memory_value(
        runtime,
        field_name=field_name,
        value=arguments["value"],
        previous_value_check=previous_value_check,
    )
    apply_memory_refresh(runtime)
    return payload


def _write_once_memory_field(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    field_name = coerce_string(arguments, "field_name")
    payload = write_once_memory_value(runtime, field_name=field_name, value=arguments["value"])
    if "error" not in payload:
        apply_memory_refresh(runtime)
    return payload


def _inject_directive(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    directive = coerce_string(arguments, "directive")
    priority = arguments.get("priority")
    if priority not in {"critical", "standard", "advisory"}:
        raise ValueError("The 'priority' argument must be one of: critical, standard, advisory.")
    expires_after_resets = arguments.get("expires_after_resets")
    if expires_after_resets is not None and (isinstance(expires_after_resets, bool) or not isinstance(expires_after_resets, int)):
        raise ValueError("The 'expires_after_resets' argument must be an integer when provided.")
    state = runtime.get_runtime_state()
    directive_id = f"directive_{uuid4().hex[:12]}"
    state.directives.append(
        AgentContextDirective(
            directive_id=directive_id,
            directive=directive,
            priority=priority,
            created_at_reset=runtime.get_reset_count(),
            expires_after_resets=expires_after_resets,
        )
    )
    apply_memory_refresh(runtime)
    return {
        "directive_id": directive_id,
        "priority": priority,
        "total_directives": len(state.directives),
    }


def _clear_memory_field(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    field_name = coerce_string(arguments, "field_name")
    reason = coerce_string(arguments, "reason")
    state = runtime.get_runtime_state()
    previous_value = deepcopy(state.memory_fields.get(field_name))
    state.memory_field_rules.setdefault(field_name, "overwrite")
    state.memory_fields[field_name] = (
        f"[cleared at step {runtime.get_cycle_index()} — reason: {reason}]"
    )
    apply_memory_refresh(runtime)
    return {
        "field_name": field_name,
        "cleared_value": previous_value,
        "reset_count": runtime.get_reset_count(),
    }


def _bulk_write_memory(runtime: ContextToolRuntime, arguments: dict[str, Any]) -> dict[str, Any]:
    writes = arguments.get("writes")
    if not isinstance(writes, list) or not writes:
        raise ValueError("The 'writes' argument must be a non-empty array.")
    state = runtime.get_runtime_state()
    candidate = deepcopy(state)
    results: list[dict[str, Any]] = []
    candidate_runtime = _candidate_runtime(runtime, candidate)
    for item in writes:
        if not isinstance(item, dict):
            raise ValueError("Each bulk memory write must be an object.")
        field_name = coerce_string(item, "field_name")
        update_rule = item.get("update_rule")
        if update_rule == "append":
            append_memory_value(candidate_runtime, field_name=field_name, value=item["value"], timestamp=False)
        elif update_rule == "overwrite":
            overwrite_memory_value(candidate_runtime, field_name=field_name, value=item["value"])
        elif update_rule == "write_once":
            result = write_once_memory_value(candidate_runtime, field_name=field_name, value=item["value"])
            if "error" in result:
                raise ValueError(f"Memory field '{field_name}' already has a value.")
        else:
            raise ValueError("Each bulk memory write must use overwrite, append, or write_once.")
        results.append({"field_name": field_name, "success": True, "update_rule": update_rule})
    _replace_state(state, candidate)
    apply_memory_refresh(runtime)
    return {
        "fields_written": len(results),
        "fields": results,
    }


def _timestamped_value(runtime: ContextToolRuntime, value: Any) -> dict[str, Any]:
    return {
        "cycle_index": runtime.get_cycle_index(),
        "reset_count": runtime.get_reset_count(),
        "value": deepcopy(value),
    }


def _current_section_content(runtime: ContextToolRuntime, section_label: str) -> str | None:
    parameter_entries, _ = split_context_window(current_context_window(runtime))
    for entry in parameter_entries:
        if str(entry.get("label")) == section_label:
            return str(entry.get("content", ""))
    return None


def _total_parameter_tokens(runtime: ContextToolRuntime) -> int:
    parameter_entries, _ = split_context_window(current_context_window(runtime))
    return sum(estimate_text_tokens(f"{entry.get('label', '')}\n{entry.get('content', '')}") for entry in parameter_entries)


def _replace_state(target: Any, source: Any) -> None:
    target.injected_sections = source.injected_sections
    target.section_overrides = source.section_overrides
    target.memory_fields = source.memory_fields
    target.memory_field_rules = source.memory_field_rules
    target.directives = source.directives
    target.checkpoints = source.checkpoints


def _candidate_runtime(runtime: ContextToolRuntime, candidate_state: Any) -> ContextToolRuntime:
    return ContextToolRuntime(
        get_context_window=runtime.get_context_window,
        get_runtime_state=lambda: candidate_state,
        save_runtime_state=runtime.save_runtime_state,
        refresh_parameters=runtime.refresh_parameters,
        get_reset_count=runtime.get_reset_count,
        get_cycle_index=runtime.get_cycle_index,
        get_system_prompt=runtime.get_system_prompt,
        run_model_subcall=runtime.run_model_subcall,
    )

__all__ = [
    "append_memory_value",
    "create_context_parameter_tools",
    "overwrite_memory_value",
    "write_once_memory_value",
]
