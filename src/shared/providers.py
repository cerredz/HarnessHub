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
GEMINI_ROLE_MAP: dict[ProviderMessageRole, str] = {
    "user": "user",
    "assistant": "model",
    "system": "user",
}

__all__ = [
    "ALLOWED_MESSAGE_ROLES",
    "GEMINI_ROLE_MAP",
    "ProviderMessage",
    "ProviderMessageRole",
    "ProviderName",
    "RequestPayload",
    "SUPPORTED_PROVIDERS",
]
