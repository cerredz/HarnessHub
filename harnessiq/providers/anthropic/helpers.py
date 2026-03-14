"""Compatibility wrappers for the Anthropic provider package."""

from __future__ import annotations

from harnessiq.providers.anthropic.messages import build_request as build_message_request
from harnessiq.providers.anthropic.tools import format_tool_definition as format_anthropic_tool_definition
from harnessiq.shared.providers import ProviderMessage
from harnessiq.shared.tools import ToolDefinition


def format_tool_definition(definition: ToolDefinition) -> dict[str, object]:
    """Translate a canonical tool definition into Anthropic's tool payload."""
    return format_anthropic_tool_definition(definition)


def build_request(
    model_name: str,
    system_prompt: str,
    messages: list[ProviderMessage],
    tools: list[ToolDefinition],
) -> dict[str, object]:
    """Build an Anthropic-style request body from canonical primitives."""
    return build_message_request(
        model_name=model_name,
        system_prompt=system_prompt,
        messages=messages,
        tools=tools,
    )
