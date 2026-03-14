"""Compatibility wrappers for the OpenAI provider package."""

from __future__ import annotations

from harnessiq.providers.openai.requests import build_request as build_chat_request
from harnessiq.providers.openai.tools import format_tool_definition as format_openai_tool_definition
from harnessiq.shared.providers import ProviderMessage
from harnessiq.shared.tools import ToolDefinition


def format_tool_definition(definition: ToolDefinition) -> dict[str, object]:
    """Translate a canonical tool definition into an OpenAI function tool."""
    return format_openai_tool_definition(definition)


def build_request(
    model_name: str,
    system_prompt: str,
    messages: list[ProviderMessage],
    tools: list[ToolDefinition],
) -> dict[str, object]:
    """Build an OpenAI-style chat request body from canonical primitives."""
    return build_chat_request(
        model_name=model_name,
        system_prompt=system_prompt,
        messages=messages,
        tools=tools,
    )
