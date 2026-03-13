"""Shared helpers for translating canonical requests into provider payloads."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

from src.tools.schemas import ToolDefinition

ProviderName = Literal["anthropic", "openai", "grok", "gemini"]
ProviderMessage = dict[str, str]
RequestPayload = dict[str, Any]
SUPPORTED_PROVIDERS: tuple[ProviderName, ...] = ("anthropic", "openai", "grok", "gemini")
_ALLOWED_MESSAGE_ROLES = frozenset({"system", "user", "assistant"})


class ProviderFormatError(ValueError):
    """Raised when a request cannot be translated into provider format."""


def normalize_messages(
    messages: list[ProviderMessage],
    *,
    allow_system: bool = True,
) -> list[ProviderMessage]:
    """Validate and copy provider-agnostic chat messages."""
    normalized: list[ProviderMessage] = []
    for message in messages:
        role = message.get("role")
        content = message.get("content")
        if role not in _ALLOWED_MESSAGE_ROLES:
            message_text = f"Unsupported message role '{role}'."
            raise ProviderFormatError(message_text)
        if role == "system" and not allow_system:
            message_text = "Inline system messages are not allowed when a top-level system prompt is used."
            raise ProviderFormatError(message_text)
        if not isinstance(content, str):
            message_text = f"Message content for role '{role}' must be a string."
            raise ProviderFormatError(message_text)
        normalized.append({"role": role, "content": content})
    return normalized


def build_openai_style_tool(definition: ToolDefinition, *, strict: bool | None = None) -> RequestPayload:
    """Translate a canonical tool definition into an OpenAI-style function tool."""
    function_payload: RequestPayload = {
        "name": definition.name,
        "description": definition.description,
        "parameters": deepcopy(definition.input_schema),
    }
    if strict is not None:
        function_payload["strict"] = strict
    return {"type": "function", "function": function_payload}


def build_anthropic_tool(definition: ToolDefinition) -> RequestPayload:
    """Translate a canonical tool definition into Anthropic's tool shape."""
    return {
        "name": definition.name,
        "description": definition.description,
        "input_schema": deepcopy(definition.input_schema),
    }


def build_gemini_tool_declaration(definition: ToolDefinition) -> RequestPayload:
    """Translate a canonical tool definition into a Gemini function declaration."""
    return {
        "name": definition.name,
        "description": definition.description,
        "parameters": deepcopy(definition.input_schema),
    }


def build_openai_style_messages(system_prompt: str, messages: list[ProviderMessage]) -> list[ProviderMessage]:
    """Represent the system prompt as a leading chat message."""
    normalized = normalize_messages(messages, allow_system=False)
    if not system_prompt:
        return normalized
    return [{"role": "system", "content": system_prompt}, *normalized]


def build_gemini_contents(messages: list[ProviderMessage]) -> list[RequestPayload]:
    """Translate canonical messages into Gemini content parts."""
    role_map = {"user": "user", "assistant": "model", "system": "user"}
    contents: list[RequestPayload] = []
    for message in normalize_messages(messages, allow_system=False):
        contents.append(
            {
                "role": role_map[message["role"]],
                "parts": [{"text": message["content"]}],
            }
        )
    return contents
