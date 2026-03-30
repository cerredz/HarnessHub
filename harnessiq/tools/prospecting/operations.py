"""
===============================================================================
File: harnessiq/tools/prospecting/operations.py

What this file does:
- Exposes the `prospecting` tool family for the HarnessIQ tool layer.
- In most packages this module is the bridge between provider-backed operations
  and the generic tool registration surface.
- Public shared Google Maps prospecting tool definitions and factories.

Use cases:
- Import this module when an agent or registry needs the `prospecting` tool
  definitions.
- Read it to see which runtime operations are intentionally surfaced as tools.

How to use it:
- Call the exported factory helpers from `harnessiq/tools/prospecting` and
  merge the resulting tools into a registry.

Intent:
- Keep the public `prospecting` tool surface small, explicit, and separate from
  provider implementation details.
===============================================================================
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from harnessiq.shared.tools import RegisteredTool, ToolDefinition

START_SEARCH = "prospecting.start_search"
RECORD_LISTING_RESULT = "prospecting.record_listing_result"
SAVE_QUALIFIED_LEAD = "prospecting.save_qualified_lead"
COMPLETE_SEARCH = "prospecting.complete_search"

ProspectingToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


def _build_tool(
    *,
    key: str,
    name: str,
    description: str,
    properties: dict[str, Any],
    required: tuple[str, ...],
) -> ToolDefinition:
    return ToolDefinition(
        key=key,
        name=name,
        description=description,
        input_schema={
            "type": "object",
            "properties": properties,
            "required": list(required),
            "additionalProperties": False,
        },
    )


def build_start_search_tool_definition() -> ToolDefinition:
    """Return the canonical definition for persisting the start of a Maps search."""
    return _build_tool(
        key=START_SEARCH,
        name="start_search",
        description="Persist the start of a Google Maps search so the run can resume after a reset.",
        properties={
            "index": {"type": "integer", "description": "Search index."},
            "query": {"type": "string", "description": "Search query."},
            "location": {"type": "string", "description": "Search location."},
        },
        required=("index", "query", "location"),
    )


def build_record_listing_result_tool_definition() -> ToolDefinition:
    """Return the canonical definition for recording a single listing evaluation."""
    return _build_tool(
        key=RECORD_LISTING_RESULT,
        name="record_listing_result",
        description="Persist progress for one evaluated listing within the active search.",
        properties={
            "search_index": {"type": "integer", "description": "Active search index."},
            "listing_position": {"type": "integer", "description": "Zero-based listing position."},
            "verdict": {
                "type": "string",
                "enum": ["QUALIFIED", "DISQUALIFIED", "SKIP"],
                "description": "Evaluation verdict.",
            },
        },
        required=("search_index", "listing_position", "verdict"),
    )


def build_save_qualified_lead_tool_definition() -> ToolDefinition:
    """Return the canonical definition for persisting a qualified lead record."""
    return _build_tool(
        key=SAVE_QUALIFIED_LEAD,
        name="save_qualified_lead",
        description="Persist one qualified lead record into durable memory for ledger export.",
        properties={
            "record": {
                "type": "object",
                "description": "Qualified lead record payload derived from evaluation output.",
                "additionalProperties": True,
            }
        },
        required=("record",),
    )


def build_complete_search_tool_definition() -> ToolDefinition:
    """Return the canonical definition for marking a Maps search complete."""
    return _build_tool(
        key=COMPLETE_SEARCH,
        name="complete_search",
        description="Persist completion metadata for a Google Maps search and clear the in-progress pointer.",
        properties={
            "search_index": {"type": "integer", "description": "Completed search index."},
            "query": {"type": "string", "description": "Search query."},
            "location": {"type": "string", "description": "Search location."},
            "listings_found": {
                "type": "integer",
                "description": "Number of listings seen for the search.",
            },
        },
        required=("search_index", "query", "location", "listings_found"),
    )


def create_start_search_tool(*, handler: ProspectingToolHandler) -> RegisteredTool:
    """Create the start_search tool with an injected handler."""
    return RegisteredTool(definition=build_start_search_tool_definition(), handler=handler)


def create_record_listing_result_tool(*, handler: ProspectingToolHandler) -> RegisteredTool:
    """Create the record_listing_result tool with an injected handler."""
    return RegisteredTool(definition=build_record_listing_result_tool_definition(), handler=handler)


def create_save_qualified_lead_tool(*, handler: ProspectingToolHandler) -> RegisteredTool:
    """Create the save_qualified_lead tool with an injected handler."""
    return RegisteredTool(definition=build_save_qualified_lead_tool_definition(), handler=handler)


def create_complete_search_tool(*, handler: ProspectingToolHandler) -> RegisteredTool:
    """Create the complete_search tool with an injected handler."""
    return RegisteredTool(definition=build_complete_search_tool_definition(), handler=handler)


__all__ = [
    "COMPLETE_SEARCH",
    "RECORD_LISTING_RESULT",
    "SAVE_QUALIFIED_LEAD",
    "START_SEARCH",
    "ProspectingToolHandler",
    "build_complete_search_tool_definition",
    "build_record_listing_result_tool_definition",
    "build_save_qualified_lead_tool_definition",
    "build_start_search_tool_definition",
    "create_complete_search_tool",
    "create_record_listing_result_tool",
    "create_save_qualified_lead_tool",
    "create_start_search_tool",
]
