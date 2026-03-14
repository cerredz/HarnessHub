"""Anthropic tool, server-tool, and MCP builders."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal, Sequence

from harnessiq.providers.base import build_anthropic_tool, omit_none_values
from harnessiq.shared.tools import ToolDefinition

ToolChoiceMode = Literal["auto", "any", "tool"]


def format_tool_definition(definition: ToolDefinition) -> dict[str, object]:
    """Translate a canonical tool definition into Anthropic's tool payload."""
    return build_custom_tool(definition)


def build_custom_tool(definition: ToolDefinition) -> dict[str, object]:
    """Build an Anthropic custom tool from canonical metadata."""
    return build_anthropic_tool(definition)


def build_tool_choice(
    mode: ToolChoiceMode = "auto",
    *,
    tool_name: str | None = None,
    disable_parallel_tool_use: bool | None = None,
) -> dict[str, object]:
    """Build the Anthropic tool-choice payload."""
    payload = {"type": "tool", "name": tool_name} if tool_name is not None else {"type": mode}
    if disable_parallel_tool_use is not None:
        payload["disable_parallel_tool_use"] = disable_parallel_tool_use
    return payload


def build_web_search_tool(
    *,
    max_uses: int | None = None,
    allowed_domains: Sequence[str] | None = None,
    blocked_domains: Sequence[str] | None = None,
    type_name: str = "web_search_20250305",
) -> dict[str, object]:
    """Build the Anthropic web search server-tool payload."""
    return omit_none_values(
        {
            "type": type_name,
            "max_uses": max_uses,
            "allowed_domains": list(allowed_domains) if allowed_domains is not None else None,
            "blocked_domains": list(blocked_domains) if blocked_domains is not None else None,
        }
    )


def build_text_editor_tool(
    *,
    type_name: str = "text_editor_20250124",
) -> dict[str, str]:
    """Build the Anthropic text editor server-tool payload."""
    return {"type": type_name}


def build_bash_tool(
    *,
    type_name: str = "bash_20250124",
) -> dict[str, str]:
    """Build the Anthropic bash server-tool payload."""
    return {"type": type_name}


def build_computer_tool(
    *,
    display_width_px: int,
    display_height_px: int,
    display_number: int = 1,
    type_name: str = "computer_20250124",
) -> dict[str, object]:
    """Build the Anthropic computer-use server-tool payload."""
    return {
        "type": type_name,
        "display_width_px": display_width_px,
        "display_height_px": display_height_px,
        "display_number": display_number,
    }


def build_mcp_server(
    *,
    name: str,
    url: str,
    authorization_token: str | None = None,
    tool_configuration: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, object]:
    """Build an Anthropic MCP server configuration payload."""
    return omit_none_values(
        {
            "name": name,
            "url": url,
            "authorization_token": authorization_token,
            "tool_configuration": deepcopy(tool_configuration) if tool_configuration is not None else None,
            "headers": deepcopy(headers) if headers is not None else None,
        }
    )
