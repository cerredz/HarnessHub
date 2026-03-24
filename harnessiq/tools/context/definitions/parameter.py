"""Tool definitions for parameter-zone context tools."""

from __future__ import annotations

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

from .. import ContextToolRuntime, build_tool_definition
from ..executors.parameter import (
    append_memory_field,
    bulk_write_memory,
    clear_memory_field,
    inject_directive,
    inject_section,
    overwrite_memory_field,
    update_section,
    write_once_memory_field,
)


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
            handler=lambda arguments: inject_section(runtime, arguments),
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
            handler=lambda arguments: update_section(runtime, arguments),
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
            handler=lambda arguments: append_memory_field(runtime, arguments),
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
            handler=lambda arguments: overwrite_memory_field(runtime, arguments),
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
            handler=lambda arguments: write_once_memory_field(runtime, arguments),
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
            handler=lambda arguments: inject_directive(runtime, arguments),
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
            handler=lambda arguments: clear_memory_field(runtime, arguments),
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
            handler=lambda arguments: bulk_write_memory(runtime, arguments),
        ),
    )


__all__ = ["create_context_parameter_tools"]
