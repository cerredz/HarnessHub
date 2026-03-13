"""Thin Gemini payload builders."""

from __future__ import annotations

from src.providers.base import ProviderMessage, build_gemini_contents, build_gemini_tool_declaration
from src.tools.schemas import ToolDefinition


def format_tool_definition(definition: ToolDefinition) -> dict[str, object]:
    """Translate a canonical tool definition into a Gemini function declaration."""
    return build_gemini_tool_declaration(definition)


def build_request(
    model_name: str,
    system_prompt: str,
    messages: list[ProviderMessage],
    tools: list[ToolDefinition],
) -> dict[str, object]:
    """Build a Gemini-style request body from canonical primitives."""
    request: dict[str, object] = {
        "model": model_name,
        "contents": build_gemini_contents(messages),
    }
    if system_prompt:
        request["system_instruction"] = {"parts": [{"text": system_prompt}]}
    if tools:
        request["tools"] = [{"functionDeclarations": [format_tool_definition(tool) for tool in tools]}]
    return request
