"""
===============================================================================
File: harnessiq/tools/context/definitions/selective.py

What this file does:
- Implements part of the context-tool system that rewrites, summarizes, or
  annotates an agent context window.
- Tool definitions for selective context tools.

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
    CONTEXT_SELECT_ANNOTATE_ENTRY,
    CONTEXT_SELECT_CHECKPOINT,
    CONTEXT_SELECT_EXTRACT_AND_COLLAPSE,
    CONTEXT_SELECT_FILTER_BY_TOOL_KEY,
    CONTEXT_SELECT_KEEP_BY_TAG,
    CONTEXT_SELECT_PROMOTE_AND_STRIP,
    CONTEXT_SELECT_SPLIT_AND_PROMOTE,
    RegisteredTool,
)

from .. import ContextToolRuntime, build_tool_definition
from ..executors.selective import (
    annotate_entry,
    checkpoint,
    extract_and_collapse,
    filter_by_tool_key,
    keep_by_tag,
    promote_and_strip,
    split_and_promote,
)


def create_context_selective_tools(runtime: ContextToolRuntime) -> tuple[RegisteredTool, ...]:
    return (
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_SELECT_EXTRACT_AND_COLLAPSE,
                name="extract_and_collapse",
                description="Keep selected transcript entries and collapse the rest.",
                properties={
                    "keep_indices": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "minItems": 1,
                    },
                    "collapse_label": {"type": "string"},
                },
                required=("keep_indices",),
            ),
            handler=lambda arguments: extract_and_collapse(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_SELECT_FILTER_BY_TOOL_KEY,
                name="filter_by_tool_key",
                description="Keep only transcript entries matching specific tool keys.",
                properties={
                    "keep_keys": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                    },
                    "include_assistant_messages": {"type": "boolean"},
                },
                required=("keep_keys",),
            ),
            handler=lambda arguments: filter_by_tool_key(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_SELECT_PROMOTE_AND_STRIP,
                name="promote_and_strip",
                description="Write one transcript entry into durable memory and remove it from the transcript.",
                properties={
                    "entry_index": {"type": "integer", "minimum": 0},
                    "target_field": {"type": "string"},
                    "update_rule": {
                        "type": "string",
                        "enum": ["overwrite", "append"],
                    },
                },
                required=("entry_index", "target_field", "update_rule"),
            ),
            handler=lambda arguments: promote_and_strip(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_SELECT_ANNOTATE_ENTRY,
                name="annotate_entry",
                description="Append a short agent note to a transcript entry.",
                properties={
                    "entry_index": {"type": "integer", "minimum": 0},
                    "annotation": {"type": "string"},
                    "tag": {"type": "string"},
                },
                required=("entry_index", "annotation"),
            ),
            handler=lambda arguments: annotate_entry(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_SELECT_CHECKPOINT,
                name="checkpoint",
                description="Persist the full current context window as an audit checkpoint.",
                properties={
                    "checkpoint_name": {"type": "string"},
                    "description": {"type": "string"},
                },
                required=("checkpoint_name",),
            ),
            handler=lambda arguments: checkpoint(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_SELECT_KEEP_BY_TAG,
                name="keep_by_tag",
                description="Keep only transcript entries annotated with a specific tag.",
                properties={
                    "tag": {"type": "string"},
                    "collapse_dropped": {"type": "boolean"},
                },
                required=("tag",),
            ),
            handler=lambda arguments: keep_by_tag(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_SELECT_SPLIT_AND_PROMOTE,
                name="split_and_promote",
                description="Promote the pre-split transcript into durable memory and keep the tail verbatim.",
                properties={
                    "split_index": {"type": "integer", "minimum": 0},
                    "target_field": {"type": "string"},
                    "summarize_before": {"type": "boolean"},
                    "model_override": {"type": "string"},
                },
                required=("split_index", "target_field"),
            ),
            handler=lambda arguments: split_and_promote(runtime, arguments),
        ),
    )


__all__ = ["create_context_selective_tools"]
