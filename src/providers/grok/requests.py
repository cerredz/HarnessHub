"""xAI/Grok request payload builders."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal, Sequence

from src.providers.base import build_openai_style_messages, omit_none_values
from src.providers.grok.tools import build_function_tool, format_tool_definition
from src.shared.providers import ProviderMessage
from src.shared.tools import ToolDefinition


def build_request(
    model_name: str,
    system_prompt: str,
    messages: list[ProviderMessage],
    tools: list[ToolDefinition],
) -> dict[str, object]:
    """Build a Grok-style request body from canonical primitives."""
    return build_chat_completion_request(
        model_name=model_name,
        system_prompt=system_prompt,
        messages=messages,
        tools=tools,
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
    return omit_none_values(
        {
            "mode": mode,
            "max_search_results": max_search_results,
            "return_citations": return_citations,
            "from_date": from_date,
            "to_date": to_date,
            "sources": list(sources) if sources is not None else None,
        }
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


def build_chat_completion_request(
    *,
    model_name: str,
    system_prompt: str,
    messages: list[ProviderMessage],
    tools: Sequence[ToolDefinition | dict[str, Any]] | None = None,
    tool_choice: str | dict[str, Any] | None = None,
    response_format: dict[str, Any] | None = None,
    search_parameters: dict[str, Any] | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    reasoning_effort: Literal["low", "medium", "high"] | None = None,
) -> dict[str, object]:
    """Build an xAI chat completions request body."""
    return omit_none_values(
        {
            "model": model_name,
            "messages": build_openai_style_messages(system_prompt, messages),
            "tools": _coerce_tool_payloads(tools),
            "tool_choice": deepcopy(tool_choice) if isinstance(tool_choice, dict) else tool_choice,
            "response_format": deepcopy(response_format) if response_format is not None else None,
            "search_parameters": deepcopy(search_parameters) if search_parameters is not None else None,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "reasoning_effort": reasoning_effort,
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
