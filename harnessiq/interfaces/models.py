"""Interface contracts for provider-backed model clients."""

from __future__ import annotations

from typing import Any, Mapping, Protocol, Sequence, runtime_checkable


@runtime_checkable
class OpenAIStyleModelClient(Protocol):
    """Describe chat-completion clients used by OpenAI-style providers."""

    def create_chat_completion(
        self,
        *,
        model_name: str,
        system_prompt: str,
        messages: list[Mapping[str, Any]],
        tools: Sequence[Any] | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        parallel_tool_calls: bool | None = None,
        reasoning_effort: str | None = None,
    ) -> Any:
        """Create one chat completion response."""


@runtime_checkable
class AnthropicModelClient(Protocol):
    """Describe the Anthropic Messages client surface used by the runtime."""

    def create_message(
        self,
        *,
        model_name: str,
        messages: list[Mapping[str, Any]],
        max_tokens: int,
        system_prompt: str | None = None,
        tools: Sequence[Any] | None = None,
        tool_choice: Mapping[str, Any] | None = None,
        temperature: float | None = None,
    ) -> Any:
        """Create one Anthropic message response."""


@runtime_checkable
class GeminiModelClient(Protocol):
    """Describe the Gemini generateContent client surface used by the runtime."""

    def generate_content(
        self,
        *,
        model_name: str,
        contents: list[Mapping[str, Any]],
        system_instruction: Mapping[str, Any] | None = None,
        tools: Sequence[Any] | None = None,
        tool_config: Mapping[str, Any] | None = None,
        generation_config: Mapping[str, Any] | None = None,
    ) -> Any:
        """Create one Gemini generateContent response."""


__all__ = [
    "AnthropicModelClient",
    "GeminiModelClient",
    "OpenAIStyleModelClient",
]
