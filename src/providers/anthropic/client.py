"""Thin Anthropic API client wrappers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from src.providers.anthropic.api import (
    DEFAULT_API_VERSION,
    DEFAULT_BASE_URL,
    build_headers,
    count_tokens_url,
    messages_url,
)
from src.providers.anthropic.messages import build_count_tokens_request, build_message_request
from src.providers.http import RequestExecutor, request_json
from src.shared.providers import ProviderMessage
from src.shared.tools import ToolDefinition


@dataclass(frozen=True, slots=True)
class AnthropicClient:
    """Minimal Anthropic client that reuses local request builders."""

    api_key: str
    base_url: str = DEFAULT_BASE_URL
    api_version: str = DEFAULT_API_VERSION
    betas: Sequence[str] | None = None
    timeout_seconds: float = 60.0
    request_executor: RequestExecutor = request_json

    def create_message(
        self,
        *,
        model_name: str,
        messages: Sequence[ProviderMessage | dict[str, Any]],
        max_tokens: int,
        system_prompt: str | Sequence[dict[str, Any]] | None = None,
        tools: Sequence[ToolDefinition | dict[str, Any]] | None = None,
        tool_choice: dict[str, Any] | None = None,
        thinking: dict[str, Any] | None = None,
        metadata: dict[str, str] | None = None,
        stop_sequences: Sequence[str] | None = None,
        temperature: float | None = None,
        mcp_servers: Sequence[dict[str, Any]] | None = None,
    ) -> Any:
        """Create an Anthropic Messages API request."""
        payload = build_message_request(
            model_name=model_name,
            messages=messages,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            tools=tools,
            tool_choice=tool_choice,
            thinking=thinking,
            metadata=metadata,
            stop_sequences=stop_sequences,
            temperature=temperature,
            mcp_servers=mcp_servers,
        )
        return self._request("POST", messages_url(self.base_url), json_body=payload)

    def count_tokens(
        self,
        *,
        model_name: str,
        messages: Sequence[ProviderMessage | dict[str, Any]],
        system_prompt: str | Sequence[dict[str, Any]] | None = None,
        tools: Sequence[ToolDefinition | dict[str, Any]] | None = None,
    ) -> Any:
        """Create an Anthropic token-count request."""
        payload = build_count_tokens_request(
            model_name=model_name,
            messages=messages,
            system_prompt=system_prompt,
            tools=tools,
        )
        return self._request("POST", count_tokens_url(self.base_url), json_body=payload)

    def _request(
        self,
        method: str,
        url: str,
        *,
        json_body: Mapping[str, Any] | None = None,
    ) -> Any:
        return self.request_executor(
            method,
            url,
            headers=build_headers(
                self.api_key,
                api_version=self.api_version,
                betas=self.betas,
            ),
            json_body=dict(json_body) if json_body is not None else None,
            timeout_seconds=self.timeout_seconds,
        )
