"""Thin OpenAI API client wrappers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from harnessiq.providers.http import RequestExecutor, request_json
from harnessiq.providers.openai.api import (
    DEFAULT_BASE_URL,
    build_headers,
    chat_completions_url,
    embeddings_url,
    models_url,
    responses_url,
)
from harnessiq.providers.openai.requests import (
    build_chat_completion_request,
    build_embedding_request,
    build_response_request,
)
from harnessiq.shared.dtos import (
    OpenAIChatCompletionRequestDTO,
    OpenAIEmbeddingRequestDTO,
    OpenAIResponseRequestDTO,
)


@dataclass(frozen=True, slots=True)
class OpenAIClient:
    """Minimal OpenAI client that reuses local request builders."""

    api_key: str
    base_url: str = DEFAULT_BASE_URL
    organization: str | None = None
    project: str | None = None
    timeout_seconds: float = 60.0
    request_executor: RequestExecutor = request_json

    def create_response(
        self,
        request: OpenAIResponseRequestDTO,
    ) -> Any:
        """Create a Responses API request."""
        payload = build_response_request(request)
        return self._request("POST", responses_url(self.base_url), json_body=payload)

    def create_chat_completion(
        self,
        request: OpenAIChatCompletionRequestDTO,
    ) -> Any:
        """Create a Chat Completions API request."""
        payload = build_chat_completion_request(request)
        return self._request("POST", chat_completions_url(self.base_url), json_body=payload)

    def create_embedding(
        self,
        request: OpenAIEmbeddingRequestDTO,
    ) -> Any:
        """Create an embeddings request."""
        payload = build_embedding_request(request)
        return self._request("POST", embeddings_url(self.base_url), json_body=payload)

    def list_models(self) -> Any:
        """List available models for the configured API key."""
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
            headers=build_headers(
                self.api_key,
                organization=self.organization,
                project=self.project,
            ),
            json_body=dict(json_body) if json_body is not None else None,
            timeout_seconds=self.timeout_seconds,
        )
