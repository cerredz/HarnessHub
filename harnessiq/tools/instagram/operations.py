"""Public shared Instagram keyword search tool definition and factory."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from harnessiq.shared.tools import RegisteredTool, ToolDefinition

SEARCH_KEYWORD = "instagram.search_keyword"

SearchKeywordHandler = Callable[[dict[str, Any]], dict[str, Any]]


def build_search_keyword_tool_definition() -> ToolDefinition:
    """Return the canonical tool definition for Instagram keyword search."""
    return ToolDefinition(
        key=SEARCH_KEYWORD,
        name="search_keyword",
        description=(
            "Run a deterministic Google site:instagram.com search for one keyword, load the search page "
            "and opened result tabs fully, extract public emails from visited pages, and persist all "
            "new leads/emails to durable memory."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "The concise Instagram creator niche keyword to search.",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of Instagram result URLs to open for this keyword.",
                },
            },
            "required": ["keyword"],
            "additionalProperties": False,
        },
    )


def create_search_keyword_tool(*, handler: SearchKeywordHandler) -> RegisteredTool:
    """Create the Instagram keyword search tool with an injected handler."""
    return RegisteredTool(definition=build_search_keyword_tool_definition(), handler=handler)


__all__ = [
    "SEARCH_KEYWORD",
    "SearchKeywordHandler",
    "build_search_keyword_tool_definition",
    "create_search_keyword_tool",
]
