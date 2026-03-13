"""Thin Gemini API client wrappers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from src.providers.gemini.api import (
    DEFAULT_API_VERSION,
    DEFAULT_BASE_URL,
    build_headers,
    cached_contents_url,
    count_tokens_url,
    generate_content_url,
    models_url,
)
from src.providers.gemini.content import (
    build_cached_content_request,
    build_count_tokens_request,
    build_generate_content_request,
)
from src.providers.http import RequestExecutor, request_json
from src.shared.tools import ToolDefinition


@dataclass(frozen=True, slots=True)
class GeminiClient:
    """Minimal Gemini client that reuses local request builders."""

    api_key: str
    base_url: str = DEFAULT_BASE_URL
    api_version: str = DEFAULT_API_VERSION
    timeout_seconds: float = 60.0
    request_executor: RequestExecutor = request_json

    def generate_content(
        self,
        *,
        model_name: str,
        contents: Sequence[dict[str, Any]],
        system_instruction: dict[str, Any] | None = None,
        tools: Sequence[ToolDefinition | dict[str, Any]] | None = None,
        tool_config: dict[str, Any] | None = None,
        generation_config: dict[str, Any] | None = None,
        cached_content: str | None = None,
    ) -> Any:
        """Create a Gemini generate-content request."""
        payload = build_generate_content_request(
            contents=contents,
            system_instruction=system_instruction,
            tools=tools,
            tool_config=tool_config,
            generation_config=generation_config,
            cached_content=cached_content,
        )
        return self._request(
            "POST",
            generate_content_url(model_name, self.api_key, base_url=self.base_url, api_version=self.api_version),
            json_body=payload,
        )

    def count_tokens(
        self,
        *,
        model_name: str,
        contents: Sequence[dict[str, Any]],
        system_instruction: dict[str, Any] | None = None,
        tools: Sequence[ToolDefinition | dict[str, Any]] | None = None,
        tool_config: dict[str, Any] | None = None,
    ) -> Any:
        """Create a Gemini count-tokens request."""
        payload = build_count_tokens_request(
            contents=contents,
            system_instruction=system_instruction,
            tools=tools,
            tool_config=tool_config,
        )
        return self._request(
            "POST",
            count_tokens_url(model_name, self.api_key, base_url=self.base_url, api_version=self.api_version),
            json_body=payload,
        )

    def create_cache(
        self,
        *,
        model_name: str,
        contents: Sequence[dict[str, Any]],
        system_instruction: dict[str, Any] | None = None,
        tools: Sequence[ToolDefinition | dict[str, Any]] | None = None,
        ttl: str | None = None,
        display_name: str | None = None,
    ) -> Any:
        """Create a Gemini cached-content request."""
        payload = build_cached_content_request(
            model_name=model_name,
            contents=contents,
            system_instruction=system_instruction,
            tools=tools,
            ttl=ttl,
            display_name=display_name,
        )
        return self._request(
            "POST",
            cached_contents_url(self.api_key, base_url=self.base_url, api_version=self.api_version),
            json_body=payload,
        )

    def list_models(self) -> Any:
        """List available Gemini models for the configured API key."""
        return self._request("GET", models_url(self.api_key, base_url=self.base_url, api_version=self.api_version))

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
            headers=build_headers(),
            json_body=dict(json_body) if json_body is not None else None,
            timeout_seconds=self.timeout_seconds,
        )
