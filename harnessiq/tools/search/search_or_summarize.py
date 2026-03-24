"""Public shared search iteration + summarization tool."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from harnessiq.shared.tools import RegisteredTool, SEARCH_OR_SUMMARIZE, ToolDefinition

SearchOrSummarizeHandler = Callable[[dict[str, Any]], dict[str, Any]]


def build_search_or_summarize_tool_definition() -> ToolDefinition:
    """Return the canonical definition for iterative search planning."""
    return ToolDefinition(
        key=SEARCH_OR_SUMMARIZE,
        name="search_or_summarize",
        description="Determine the next search query and optionally summarize/prune prior search history when the unsummarized threshold is reached.",
        input_schema={
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
    )


def create_search_or_summarize_tool(*, handler: SearchOrSummarizeHandler) -> RegisteredTool:
    """Create the public shared search planning tool with an injected handler."""
    return RegisteredTool(definition=build_search_or_summarize_tool_definition(), handler=handler)


__all__ = [
    "SearchOrSummarizeHandler",
    "build_search_or_summarize_tool_definition",
    "create_search_or_summarize_tool",
]
