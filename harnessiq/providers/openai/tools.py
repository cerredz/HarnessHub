"""OpenAI tool and tool-choice builders."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal, Sequence

from harnessiq.providers.base import build_openai_style_tool, omit_none_values
from harnessiq.shared.providers import RequestPayload
from harnessiq.shared.tools import ToolDefinition

ToolChoiceMode = Literal["auto", "none", "required"]


def format_tool_definition(definition: ToolDefinition) -> dict[str, object]:
    """Translate a canonical tool definition into an OpenAI function tool."""
    return build_function_tool(definition, strict=False)


def build_function_tool(
    definition: ToolDefinition,
    *,
    strict: bool | None = None,
) -> dict[str, object]:
    """Build an OpenAI function tool from canonical metadata."""
    return build_openai_style_tool(definition, strict=strict)


def build_tool_choice(
    mode: ToolChoiceMode | None = None,
    *,
    tool_name: str | None = None,
) -> str | dict[str, object]:
    """Build the OpenAI tool choice payload."""
    if tool_name is not None:
        return {
            "type": "function",
            "function": {"name": tool_name},
        }
    return mode or "auto"


def build_web_search_location(
    *,
    city: str | None = None,
    country: str | None = None,
    region: str | None = None,
    timezone: str | None = None,
) -> RequestPayload:
    """Build the nested location payload used by web search."""
    return omit_none_values(
        {
            "city": city,
            "country": country,
            "region": region,
            "timezone": timezone,
        }
    )


def build_file_search_tool(
    vector_store_ids: Sequence[str],
    *,
    filters: dict[str, Any] | None = None,
    max_num_results: int | None = None,
) -> dict[str, object]:
    """Build the Responses API file search tool payload."""
    return omit_none_values(
        {
            "type": "file_search",
            "vector_store_ids": list(vector_store_ids),
            "filters": deepcopy(filters) if filters is not None else None,
            "max_num_results": max_num_results,
        }
    )


def build_web_search_tool(
    *,
    user_location: dict[str, Any] | None = None,
    search_context_size: Literal["low", "medium", "high"] | None = None,
) -> dict[str, object]:
    """Build the Responses API web search tool payload."""
    return omit_none_values(
        {
            "type": "web_search_preview",
            "user_location": deepcopy(user_location) if user_location is not None else None,
            "search_context_size": search_context_size,
        }
    )


def build_code_interpreter_tool(
    *,
    container: str | dict[str, Any] | None = None,
) -> dict[str, object]:
    """Build the Responses API code interpreter tool payload."""
    return omit_none_values(
        {
            "type": "code_interpreter",
            "container": deepcopy(container) if isinstance(container, dict) else container,
        }
    )


def build_image_generation_tool(
    *,
    background: Literal["transparent", "opaque"] | None = None,
    output_format: Literal["png", "jpeg", "webp"] | None = None,
    quality: Literal["low", "medium", "high"] | None = None,
    size: str | None = None,
) -> dict[str, object]:
    """Build the Responses API image generation tool payload."""
    return omit_none_values(
        {
            "type": "image_generation",
            "background": background,
            "output_format": output_format,
            "quality": quality,
            "size": size,
        }
    )


def build_computer_use_tool(
    *,
    display_width: int,
    display_height: int,
    environment: Literal["browser", "mac", "windows", "ubuntu"],
) -> dict[str, object]:
    """Build the computer use preview tool payload."""
    return {
        "type": "computer_use_preview",
        "display_width": display_width,
        "display_height": display_height,
        "environment": environment,
    }


def build_mcp_tool(
    *,
    server_label: str,
    server_url: str | None = None,
    connector_id: str | None = None,
    authorization: str | None = None,
    headers: dict[str, str] | None = None,
    allowed_tools: Sequence[str] | None = None,
    require_approval: Literal["always", "never"] | None = None,
) -> dict[str, object]:
    """Build the Responses API remote MCP tool payload."""
    return omit_none_values(
        {
            "type": "mcp",
            "server_label": server_label,
            "server_url": server_url,
            "connector_id": connector_id,
            "authorization": authorization,
            "headers": deepcopy(headers) if headers is not None else None,
            "allowed_tools": list(allowed_tools) if allowed_tools is not None else None,
            "require_approval": require_approval,
        }
    )
