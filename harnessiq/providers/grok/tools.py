"""xAI/Grok tool and tool-choice builders."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal, Sequence

from harnessiq.providers.base import build_openai_style_tool, omit_none_values
from harnessiq.shared.tools import ToolDefinition

ToolChoiceMode = Literal["auto", "none", "required"]


def format_tool_definition(definition: ToolDefinition) -> dict[str, object]:
    """Translate a canonical tool definition into an xAI function tool."""
    return build_function_tool(definition)


def build_function_tool(definition: ToolDefinition) -> dict[str, object]:
    """Build an xAI function tool from canonical metadata."""
    return build_openai_style_tool(definition)


def build_tool_choice(
    mode: ToolChoiceMode | None = None,
    *,
    tool_name: str | None = None,
) -> str | dict[str, object]:
    """Build the xAI tool choice payload."""
    if tool_name is not None:
        return {
            "type": "function",
            "function": {"name": tool_name},
        }
    return mode or "auto"


def build_web_search_tool(
    *,
    search_parameters: dict[str, Any] | None = None,
) -> dict[str, object]:
    """Build the xAI web search tool payload."""
    return omit_none_values(
        {
            "type": "web_search",
            "search_parameters": deepcopy(search_parameters) if search_parameters is not None else None,
        }
    )


def build_x_search_tool(
    *,
    search_parameters: dict[str, Any] | None = None,
) -> dict[str, object]:
    """Build the xAI X-search tool payload."""
    return omit_none_values(
        {
            "type": "x_search",
            "search_parameters": deepcopy(search_parameters) if search_parameters is not None else None,
        }
    )


def build_code_execution_tool() -> dict[str, str]:
    """Build the xAI code execution tool payload."""
    return {"type": "code_execution"}


def build_collections_search_tool(
    *,
    collection_ids: Sequence[str] | None = None,
    file_ids: Sequence[str] | None = None,
    max_num_results: int | None = None,
) -> dict[str, object]:
    """Build the xAI collections/file search tool payload."""
    return omit_none_values(
        {
            "type": "collections_search",
            "collection_ids": list(collection_ids) if collection_ids is not None else None,
            "file_ids": list(file_ids) if file_ids is not None else None,
            "max_num_results": max_num_results,
        }
    )


def build_mcp_tool(
    *,
    server_label: str,
    server_url: str | None = None,
    authorization: str | None = None,
    headers: dict[str, str] | None = None,
    allowed_tools: Sequence[str] | None = None,
) -> dict[str, object]:
    """Build the xAI remote MCP tool payload."""
    return omit_none_values(
        {
            "type": "mcp",
            "server_label": server_label,
            "server_url": server_url,
            "authorization": authorization,
            "headers": deepcopy(headers) if headers is not None else None,
            "allowed_tools": list(allowed_tools) if allowed_tools is not None else None,
        }
    )
