"""
===============================================================================
File: harnessiq/tools/context/definitions/structural.py

What this file does:
- Implements part of the context-tool system that rewrites, summarizes, or
  annotates an agent context window.
- Tool definitions for structural context tools.

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
    CONTEXT_STRUCT_COLLAPSE_CHAIN,
    CONTEXT_STRUCT_DEDUPLICATE,
    CONTEXT_STRUCT_FOLD_BY_TOOL_KEY,
    CONTEXT_STRUCT_MERGE_SECTIONS,
    CONTEXT_STRUCT_REDACT,
    CONTEXT_STRUCT_REORDER,
    CONTEXT_STRUCT_STRIP_OUTPUTS,
    CONTEXT_STRUCT_TRUNCATE,
    CONTEXT_STRUCT_WINDOW_SLICE,
    RegisteredTool,
)

from .. import ContextToolRuntime, build_tool_definition
from ..executors.structural import (
    collapse_chain,
    deduplicate,
    fold_by_tool_key,
    merge_sections,
    redact,
    reorder,
    strip_outputs,
    truncate,
    window_slice,
)


def create_context_structural_tools(runtime: ContextToolRuntime) -> tuple[RegisteredTool, ...]:
    return (
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_STRUCT_TRUNCATE,
                name="truncate",
                description="Keep only the N most recent transcript entries.",
                properties={"keep_last": {"type": "integer", "minimum": 1}},
                required=("keep_last",),
            ),
            handler=lambda arguments: truncate(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_STRUCT_STRIP_OUTPUTS,
                name="strip_outputs",
                description="Replace targeted tool-result bodies with a stripped-output marker.",
                properties={
                    "tool_keys": {"type": "array", "items": {"type": "string"}},
                    "preserve_errors": {"type": "boolean"},
                },
            ),
            handler=lambda arguments: strip_outputs(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_STRUCT_DEDUPLICATE,
                name="deduplicate",
                description="Collapse near-duplicate tool results.",
                properties={
                    "tool_keys": {"type": "array", "items": {"type": "string"}},
                    "similarity_threshold": {"type": "number", "minimum": 0, "maximum": 1},
                    "max_gap": {"type": "integer", "minimum": 0},
                },
            ),
            handler=lambda arguments: deduplicate(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_STRUCT_REORDER,
                name="reorder",
                description="Move one transcript entry to the most recent position.",
                properties={"entry_index": {"type": "integer", "minimum": 0}},
                required=("entry_index",),
            ),
            handler=lambda arguments: reorder(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_STRUCT_COLLAPSE_CHAIN,
                name="collapse_chain",
                description="Collapse a contiguous transcript range into one summary entry.",
                properties={
                    "start_index": {"type": "integer", "minimum": 0},
                    "end_index": {"type": "integer", "minimum": 0},
                    "summary": {"type": "string"},
                },
                required=("start_index", "end_index", "summary"),
            ),
            handler=lambda arguments: collapse_chain(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_STRUCT_REDACT,
                name="redact",
                description="Redact matching patterns from transcript entries.",
                properties={
                    "patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                    },
                    "redaction_label": {"type": "string"},
                },
                required=("patterns",),
            ),
            handler=lambda arguments: redact(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_STRUCT_MERGE_SECTIONS,
                name="merge_sections",
                description="Merge two separated transcript ranges into one coherent block.",
                properties={
                    "range_a": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "minItems": 2,
                        "maxItems": 2,
                    },
                    "range_b": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "minItems": 2,
                        "maxItems": 2,
                    },
                    "merge_label": {"type": "string"},
                    "model_override": {"type": "string"},
                },
                required=("range_a", "range_b"),
            ),
            handler=lambda arguments: merge_sections(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_STRUCT_WINDOW_SLICE,
                name="window_slice",
                description="Keep only a contiguous slice of transcript history.",
                properties={
                    "start_index": {"type": "integer", "minimum": 0},
                    "end_index": {"type": "integer", "minimum": 0},
                    "preserve_latest_n": {"type": "integer", "minimum": 0},
                },
                required=("start_index", "end_index"),
            ),
            handler=lambda arguments: window_slice(runtime, arguments),
        ),
        RegisteredTool(
            definition=build_tool_definition(
                key=CONTEXT_STRUCT_FOLD_BY_TOOL_KEY,
                name="fold_by_tool_key",
                description="Fold older entries for one tool key into a merged summary block.",
                properties={
                    "tool_key": {"type": "string"},
                    "keep_latest_n": {"type": "integer", "minimum": 0},
                    "model_override": {"type": "string"},
                },
                required=("tool_key",),
            ),
            handler=lambda arguments: fold_by_tool_key(runtime, arguments),
        ),
    )


__all__ = ["create_context_structural_tools"]
