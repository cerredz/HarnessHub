"""Thin Anthropic payload builders."""

from __future__ import annotations

from src.providers.base import build_anthropic_tool, normalize_messages
from src.shared.providers import ProviderMessage
from src.shared.tools import ToolDefinition


def format_tool_definition(definition: ToolDefinition) -> dict[str, object]:
    """Translate a canonical tool definition into Anthropic's tool payload."""
    return build_anthropic_tool(definition)


def build_request(
    model_name: str,
    system_prompt: str,
    messages: list[ProviderMessage],
    tools: list[ToolDefinition],
) -> dict[str, object]:
    """Build an Anthropic-style request body from canonical primitives."""
    return {
        "model": model_name,
        "system": system_prompt,
        "messages": normalize_messages(messages, allow_system=False),
        "tools": [format_tool_definition(tool) for tool in tools],
    }
