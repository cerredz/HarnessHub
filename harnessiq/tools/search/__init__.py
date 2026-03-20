"""Shared search tool factories."""

from .search_or_summarize import (
    build_search_or_summarize_tool_definition,
    create_search_or_summarize_tool,
)

__all__ = [
    "build_search_or_summarize_tool_definition",
    "create_search_or_summarize_tool",
]
