"""Thin OpenAI API client wrappers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

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
from harnessiq.shared.tools import ToolDefinition


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
        *,
        model_name: str,
        input_items: str | Sequence[dict[str, Any]],
        instructions: str | None = None,
        tools: Sequence[ToolDefinition | dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        text: dict[str, Any] | None = None,
        metadata: dict[str, str] | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        parallel_tool_calls: bool | None = None,
    ) -> Any:
        """Create a Responses API request."""
        payload = build_response_request(
            model_name=model_name,
            input_items=input_items,
            instructions=instructions,
            tools=tools,
            tool_choice=tool_choice,
            text=text,
            metadata=metadata,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            parallel_tool_calls=parallel_tool_calls,
        )
        return self._request("POST", responses_url(self.base_url), json_body=payload)

    def create_chat_completion(
        self,
        *,
        model_name: str,
        system_prompt: str,
        messages: list[dict[str, str]],
        tools: Sequence[ToolDefinition | dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        response_format: dict[str, Any] | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        parallel_tool_calls: bool | None = None,
    ) -> Any:
        """Create a Chat Completions API request."""
        payload = build_chat_completion_request(
            model_name=model_name,
            system_prompt=system_prompt,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            response_format=response_format,
            max_tokens=max_tokens,
            temperature=temperature,
            parallel_tool_calls=parallel_tool_calls,
        )
        return self._request("POST", chat_completions_url(self.base_url), json_body=payload)

    def create_embedding(
        self,
        *,
        model_name: str,
        input_value: str | Sequence[str] | Sequence[int] | Sequence[Sequence[int]],
        dimensions: int | None = None,
        encoding_format: str | None = None,
        user: str | None = None,
    ) -> Any:
        """Create an embeddings request."""
        payload = build_embedding_request(
            model_name=model_name,
            input_value=input_value,
            dimensions=dimensions,
            encoding_format=encoding_format,
            user=user,
        )
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
