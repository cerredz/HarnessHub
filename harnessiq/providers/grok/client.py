"""Thin xAI/Grok API client wrappers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from harnessiq.providers.grok.api import DEFAULT_BASE_URL, build_headers, chat_completions_url, models_url
from harnessiq.providers.grok.requests import build_chat_completion_request
from harnessiq.providers.http import RequestExecutor, request_json
from harnessiq.shared.dtos import GrokChatCompletionRequestDTO


@dataclass(frozen=True, slots=True)
class GrokClient:
    """Minimal xAI client that reuses local request builders."""

    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 60.0
    request_executor: RequestExecutor = request_json

    def create_chat_completion(
        self,
        request: GrokChatCompletionRequestDTO,
    ) -> Any:
        """Create an xAI chat completions request."""
        payload = build_chat_completion_request(request)
        return self._request("POST", chat_completions_url(self.base_url), json_body=payload)

    def list_models(self) -> Any:
        """List available models for the configured xAI API key."""
        return self._request("GET", models_url(self.base_url))

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
            headers=build_headers(self.api_key),
            json_body=dict(json_body) if json_body is not None else None,
            timeout_seconds=self.timeout_seconds,
        )
