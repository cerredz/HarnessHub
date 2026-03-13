"""Thin Grok payload builders."""

from __future__ import annotations

from src.providers.base import ProviderMessage, build_openai_style_messages, build_openai_style_tool
from src.tools.schemas import ToolDefinition


def format_tool_definition(definition: ToolDefinition) -> dict[str, object]:
    """Translate a canonical tool definition into a Grok function tool payload."""
    return build_openai_style_tool(definition)


def build_request(
    model_name: str,
    system_prompt: str,
    messages: list[ProviderMessage],
    tools: list[ToolDefinition],
) -> dict[str, object]:
    """Build a Grok-style request body from canonical primitives."""
    return {
        "model": model_name,
        "messages": build_openai_style_messages(system_prompt, messages),
        "tools": [format_tool_definition(tool) for tool in tools],
    }
