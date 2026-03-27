"""Thin Anthropic API client wrappers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from harnessiq.providers.anthropic.api import (
    DEFAULT_API_VERSION,
    DEFAULT_BASE_URL,
    build_headers,
    count_tokens_url,
    messages_url,
)
from harnessiq.providers.anthropic.messages import build_count_tokens_request, build_message_request
from harnessiq.providers.http import RequestExecutor, request_json
from harnessiq.shared.dtos import AnthropicCountTokensRequestDTO, AnthropicMessageRequestDTO


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
        request: AnthropicMessageRequestDTO,
    ) -> Any:
        """Create an Anthropic Messages API request."""
        payload = build_message_request(request)
        return self._request("POST", messages_url(self.base_url), json_body=payload)

    def count_tokens(
        self,
        request: AnthropicCountTokensRequestDTO,
    ) -> Any:
        """Create an Anthropic token-count request."""
        payload = build_count_tokens_request(request)
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
