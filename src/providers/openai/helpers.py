"""Thin OpenAI payload builders."""

from __future__ import annotations

from src.providers.base import build_openai_style_messages, build_openai_style_tool
from src.shared.providers import ProviderMessage
from src.shared.tools import ToolDefinition


def format_tool_definition(definition: ToolDefinition) -> dict[str, object]:
    """Translate a canonical tool definition into an OpenAI function tool."""
    return build_openai_style_tool(definition, strict=False)


def build_request(
    model_name: str,
    system_prompt: str,
    messages: list[ProviderMessage],
    tools: list[ToolDefinition],
) -> dict[str, object]:
    """Build an OpenAI-style chat request body from canonical primitives."""
    return {
        "model": model_name,
        "messages": build_openai_style_messages(system_prompt, messages),
        "tools": [format_tool_definition(tool) for tool in tools],
    }
