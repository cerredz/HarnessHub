"""Thin Gemini API client wrappers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from harnessiq.providers.gemini.api import (
    DEFAULT_API_VERSION,
    DEFAULT_BASE_URL,
    build_headers,
    cached_contents_url,
    count_tokens_url,
    generate_content_url,
    models_url,
)
from harnessiq.providers.gemini.content import (
    build_cached_content_request,
    build_count_tokens_request,
    build_generate_content_request,
)
from harnessiq.providers.http import RequestExecutor, request_json
from harnessiq.shared.dtos import GeminiCacheCreateRequestDTO, GeminiCountTokensRequestDTO, GeminiGenerateContentRequestDTO


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
        request: GeminiGenerateContentRequestDTO,
    ) -> Any:
        """Create a Gemini generate-content request."""
        payload = build_generate_content_request(request)
        return self._request(
            "POST",
            generate_content_url(request.model_name, self.api_key, base_url=self.base_url, api_version=self.api_version),
            json_body=payload,
        )

    def count_tokens(
        self,
        request: GeminiCountTokensRequestDTO,
    ) -> Any:
        """Create a Gemini count-tokens request."""
        payload = build_count_tokens_request(request)
        return self._request(
            "POST",
            count_tokens_url(request.model_name, self.api_key, base_url=self.base_url, api_version=self.api_version),
            json_body=payload,
        )

    def create_cache(
        self,
        request: GeminiCacheCreateRequestDTO,
    ) -> Any:
        """Create a Gemini cached-content request."""
        payload = build_cached_content_request(request)
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
