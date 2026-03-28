"""xAI/Grok request payload builders."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal, Sequence

from harnessiq.providers.base import build_openai_style_messages, omit_none_values
from harnessiq.providers.grok.tools import build_function_tool, format_tool_definition
from harnessiq.shared.dtos import GrokChatCompletionRequestDTO, GrokSearchParametersDTO, ProviderMessageDTO
from harnessiq.shared.tools import ToolDefinition


def build_request(
    model_name: str,
    system_prompt: str,
    messages: list[ProviderMessageDTO],
    tools: list[ToolDefinition],
) -> dict[str, object]:
    """Build a Grok-style request body from canonical primitives."""
    return build_chat_completion_request(
        GrokChatCompletionRequestDTO(
            model_name=model_name,
            system_prompt=system_prompt,
            messages=tuple(messages),
            tools=tuple(tools),
        )
    )


def build_search_parameters(
    *,
    mode: Literal["auto", "on", "off"] | None = None,
    max_search_results: int | None = None,
    return_citations: bool | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    sources: Sequence[Literal["web", "x"]] | None = None,
) -> dict[str, object]:
    """Build xAI search parameter configuration."""
    return GrokSearchParametersDTO(
        mode=mode,
        max_search_results=max_search_results,
        return_citations=return_citations,
        from_date=from_date,
        to_date=to_date,
        sources=tuple(sources or ()),
    )


def build_response_format_json_schema(
    name: str,
    schema: dict[str, Any],
    *,
    description: str | None = None,
    strict: bool | None = None,
) -> dict[str, object]:
    """Build a structured-output response format payload."""
    json_schema = omit_none_values(
        {
            "name": name,
            "description": description,
            "schema": deepcopy(schema),
            "strict": strict,
        }
    )
    return {
        "type": "json_schema",
        "json_schema": json_schema,
    }


def build_response_format_json_object() -> dict[str, str]:
    """Build a JSON-mode response format payload."""
    return {"type": "json_object"}


def build_chat_completion_request(request: GrokChatCompletionRequestDTO) -> dict[str, object]:
    """Build an xAI chat completions request body."""
    return omit_none_values(
        {
            "model": request.model_name,
            "messages": [message.to_dict() for message in build_openai_style_messages(request.system_prompt, request.messages)],
            "tools": _coerce_tool_payloads(request.tools),
            "tool_choice": deepcopy(request.tool_choice) if isinstance(request.tool_choice, dict) else request.tool_choice,
            "response_format": deepcopy(request.response_format) if request.response_format is not None else None,
            "search_parameters": request.search_parameters.to_dict() if isinstance(request.search_parameters, GrokSearchParametersDTO) else deepcopy(request.search_parameters),
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "reasoning_effort": request.reasoning_effort,
        }
    )


def _coerce_tool_payloads(
    tools: Sequence[ToolDefinition | dict[str, Any]] | None,
) -> list[dict[str, Any]] | None:
    if not tools:
        return None
    payloads: list[dict[str, Any]] = []
    for tool in tools:
        if isinstance(tool, ToolDefinition):
            payloads.append(build_function_tool(tool))
        else:
            payloads.append(deepcopy(tool))
    return payloads
