"""Shared provider constants and aliases."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

ProviderName = Literal["anthropic", "openai", "grok", "gemini"]
ProviderMessageRole = Literal["system", "user", "assistant"]
RequestPayload = dict[str, Any]


class ProviderMessage(TypedDict):
    """Provider-agnostic chat message shape."""

    role: ProviderMessageRole
    content: str


SUPPORTED_PROVIDERS: tuple[ProviderName, ...] = ("anthropic", "openai", "grok", "gemini")
ALLOWED_MESSAGE_ROLES: frozenset[ProviderMessageRole] = frozenset({"system", "user", "assistant"})
