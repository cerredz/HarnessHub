"""Interface contracts for provider-backed model clients."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from harnessiq.shared.dtos import (
    AnthropicMessageRequestDTO,
    GeminiGenerateContentRequestDTO,
    OpenAIChatCompletionRequestDTO,
)


@runtime_checkable
class OpenAIStyleModelClient(Protocol):
    """Describe chat-completion clients used by OpenAI-style providers."""

    def create_chat_completion(
        self,
        request: OpenAIChatCompletionRequestDTO,
    ) -> Any:
        """Create one chat completion response."""


@runtime_checkable
class AnthropicModelClient(Protocol):
    """Describe the Anthropic Messages client surface used by the runtime."""

    def create_message(
        self,
        request: AnthropicMessageRequestDTO,
    ) -> Any:
        """Create one Anthropic message response."""


@runtime_checkable
class GeminiModelClient(Protocol):
    """Describe the Gemini generateContent client surface used by the runtime."""

    def generate_content(
        self,
        request: GeminiGenerateContentRequestDTO,
    ) -> Any:
        """Create one Gemini generateContent response."""


__all__ = [
    "AnthropicModelClient",
    "GeminiModelClient",
    "OpenAIStyleModelClient",
]
