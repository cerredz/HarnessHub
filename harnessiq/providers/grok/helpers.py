"""Compatibility wrappers for the Grok provider package."""

from __future__ import annotations

from harnessiq.providers.grok.requests import build_request as build_chat_request
from harnessiq.providers.grok.tools import format_tool_definition as format_grok_tool_definition
from harnessiq.shared.dtos import ProviderMessageDTO
from harnessiq.shared.tools import ToolDefinition


def format_tool_definition(definition: ToolDefinition) -> dict[str, object]:
    """Translate a canonical tool definition into a Grok function tool payload."""
    return format_grok_tool_definition(definition)


def build_request(
    model_name: str,
    system_prompt: str,
    messages: list[ProviderMessageDTO],
    tools: list[ToolDefinition],
) -> dict[str, object]:
    """Build a Grok-style request body from canonical primitives."""
    return build_chat_request(
        model_name=model_name,
        system_prompt=system_prompt,
        messages=messages,
        tools=tools,
    )
