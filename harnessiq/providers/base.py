"""Shared helpers for translating canonical requests into provider payloads."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from harnessiq.shared.dtos import GeminiContentDTO, ProviderMessageDTO
from harnessiq.shared.providers import (
    ALLOWED_MESSAGE_ROLES,
    GEMINI_ROLE_MAP,
    ProviderFormatError,
    RequestPayload,
)
from harnessiq.shared.tools import ToolDefinition


def normalize_messages(
    messages: Sequence[ProviderMessageDTO],
    *,
    allow_system: bool = True,
) -> list[ProviderMessageDTO]:
    """Validate and copy provider-agnostic chat messages."""
    normalized: list[ProviderMessageDTO] = []
    for message in messages:
        role = message.role
        content = message.content
        if role not in ALLOWED_MESSAGE_ROLES:
            message_text = f"Unsupported message role '{role}'."
            raise ProviderFormatError(message_text)
        if role == "system" and not allow_system:
            message_text = "Inline system messages are not allowed when a top-level system prompt is used."
            raise ProviderFormatError(message_text)
        if not isinstance(content, str):
            message_text = f"Message content for role '{role}' must be a string."
            raise ProviderFormatError(message_text)
        normalized.append(ProviderMessageDTO(role=role, content=content))
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


def build_openai_style_messages(system_prompt: str, messages: Sequence[ProviderMessageDTO]) -> list[ProviderMessageDTO]:
    """Represent the system prompt as a leading chat message."""
    normalized = normalize_messages(messages, allow_system=False)
    if not system_prompt:
        return normalized
    return [ProviderMessageDTO(role="system", content=system_prompt), *normalized]


def build_gemini_contents(messages: Sequence[ProviderMessageDTO]) -> list[GeminiContentDTO]:
    """Translate canonical messages into Gemini content parts."""
    contents: list[GeminiContentDTO] = []
    for message in normalize_messages(messages, allow_system=False):
        contents.append(
            GeminiContentDTO(
                role=GEMINI_ROLE_MAP[message.role],
                parts=({"text": message.content},),
            )
        )
    return contents


def omit_none_values(payload: Mapping[str, Any]) -> RequestPayload:
    """Return a copy of a mapping without keys whose value is ``None``."""
    return {key: deepcopy(value) for key, value in payload.items() if value is not None}
