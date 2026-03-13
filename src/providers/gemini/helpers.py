"""Compatibility wrappers for the Gemini provider package."""

from __future__ import annotations

from src.providers.gemini.content import build_request as build_compatibility_request
from src.providers.gemini.tools import format_tool_definition as format_gemini_tool_definition
from src.shared.providers import ProviderMessage
from src.shared.tools import ToolDefinition


def format_tool_definition(definition: ToolDefinition) -> dict[str, object]:
    """Translate a canonical tool definition into a Gemini function declaration."""
    return format_gemini_tool_definition(definition)


def build_request(
    model_name: str,
    system_prompt: str,
    messages: list[ProviderMessage],
    tools: list[ToolDefinition],
) -> dict[str, object]:
    """Build a Gemini-style request body from canonical primitives."""
    return build_compatibility_request(
        model_name=model_name,
        system_prompt=system_prompt,
        messages=messages,
        tools=tools,
    )
