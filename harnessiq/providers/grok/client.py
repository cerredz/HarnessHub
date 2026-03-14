"""Thin xAI/Grok API client wrappers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping, Sequence

from harnessiq.providers.grok.api import DEFAULT_BASE_URL, build_headers, chat_completions_url, models_url
from harnessiq.providers.grok.requests import build_chat_completion_request
from harnessiq.providers.http import RequestExecutor, request_json
from harnessiq.shared.tools import ToolDefinition


@dataclass(frozen=True, slots=True)
class GrokClient:
    """Minimal xAI client that reuses local request builders."""

    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 60.0
    request_executor: RequestExecutor = request_json

    def create_chat_completion(
        self,
        *,
        model_name: str,
        system_prompt: str,
        messages: list[dict[str, str]],
        tools: Sequence[ToolDefinition | dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = None,
        response_format: dict[str, Any] | None = None,
        search_parameters: dict[str, Any] | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        reasoning_effort: Literal["low", "medium", "high"] | None = None,
    ) -> Any:
        """Create an xAI chat completions request."""
        payload = build_chat_completion_request(
            model_name=model_name,
            system_prompt=system_prompt,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            response_format=response_format,
            search_parameters=search_parameters,
            max_tokens=max_tokens,
            temperature=temperature,
            reasoning_effort=reasoning_effort,
        )
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
