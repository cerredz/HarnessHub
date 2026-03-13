"""Gemini content, generation-config, and caching builders."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal, Sequence

from src.providers.base import build_gemini_contents, omit_none_values
from src.providers.gemini.tools import build_function_tool
from src.shared.providers import ProviderMessage
from src.shared.tools import ToolDefinition

ContentRole = Literal["user", "model"]


def build_request(
    model_name: str,
    system_prompt: str,
    messages: list[ProviderMessage],
    tools: list[ToolDefinition],
) -> dict[str, object]:
    """Build a Gemini-style compatibility request body from canonical primitives."""
    request: dict[str, object] = {
        "model": model_name,
        "contents": build_gemini_contents(messages),
    }
    if system_prompt:
        request["system_instruction"] = {"parts": [{"text": system_prompt}]}
    if tools:
        request["tools"] = [build_function_tool(tools)]
    return request


def build_text_part(text: str) -> dict[str, str]:
    """Build a Gemini text part."""
    return {"text": text}


def build_inline_data_part(*, mime_type: str, data: str) -> dict[str, object]:
    """Build a Gemini inline-data part."""
    return {"inlineData": {"mimeType": mime_type, "data": data}}


def build_file_data_part(*, mime_type: str, file_uri: str) -> dict[str, object]:
    """Build a Gemini file-data part."""
    return {"fileData": {"mimeType": mime_type, "fileUri": file_uri}}


def build_content(
    role: ContentRole,
    parts: Sequence[dict[str, Any]],
) -> dict[str, object]:
    """Build a Gemini content item."""
    return {
        "role": role,
        "parts": [deepcopy(part) for part in parts],
    }


def build_system_instruction(parts: str | Sequence[dict[str, Any]]) -> dict[str, object]:
    """Build the Gemini system-instruction payload."""
    if isinstance(parts, str):
        normalized_parts = [build_text_part(parts)]
    else:
        normalized_parts = [deepcopy(part) for part in parts]
    return {"parts": normalized_parts}


def build_generation_config(
    *,
    temperature: float | None = None,
    top_p: float | None = None,
    top_k: int | None = None,
    max_output_tokens: int | None = None,
    response_mime_type: str | None = None,
    response_schema: dict[str, Any] | None = None,
) -> dict[str, object]:
    """Build Gemini generation configuration."""
    return omit_none_values(
        {
            "temperature": temperature,
            "topP": top_p,
            "topK": top_k,
            "maxOutputTokens": max_output_tokens,
            "responseMimeType": response_mime_type,
            "responseSchema": deepcopy(response_schema) if response_schema is not None else None,
        }
    )


def build_generate_content_request(
    *,
    contents: Sequence[dict[str, Any]],
    system_instruction: dict[str, Any] | None = None,
    tools: Sequence[ToolDefinition | dict[str, Any]] | None = None,
    tool_config: dict[str, Any] | None = None,
    generation_config: dict[str, Any] | None = None,
    cached_content: str | None = None,
) -> dict[str, object]:
    """Build a Gemini generate-content request body."""
    return omit_none_values(
        {
            "contents": [deepcopy(content) for content in contents],
            "systemInstruction": deepcopy(system_instruction) if system_instruction is not None else None,
            "tools": _coerce_tools(tools),
            "toolConfig": deepcopy(tool_config) if tool_config is not None else None,
            "generationConfig": deepcopy(generation_config) if generation_config is not None else None,
            "cachedContent": cached_content,
        }
    )


def build_count_tokens_request(
    *,
    contents: Sequence[dict[str, Any]],
    system_instruction: dict[str, Any] | None = None,
    tools: Sequence[ToolDefinition | dict[str, Any]] | None = None,
    tool_config: dict[str, Any] | None = None,
) -> dict[str, object]:
    """Build a Gemini count-tokens request body."""
    return omit_none_values(
        {
            "contents": [deepcopy(content) for content in contents],
            "systemInstruction": deepcopy(system_instruction) if system_instruction is not None else None,
            "tools": _coerce_tools(tools),
            "toolConfig": deepcopy(tool_config) if tool_config is not None else None,
        }
    )


def build_cached_content_request(
    *,
    model_name: str,
    contents: Sequence[dict[str, Any]],
    system_instruction: dict[str, Any] | None = None,
    tools: Sequence[ToolDefinition | dict[str, Any]] | None = None,
    ttl: str | None = None,
    display_name: str | None = None,
) -> dict[str, object]:
    """Build a Gemini cached-content create request body."""
    return omit_none_values(
        {
            "model": model_name,
            "contents": [deepcopy(content) for content in contents],
            "systemInstruction": deepcopy(system_instruction) if system_instruction is not None else None,
            "tools": _coerce_tools(tools),
            "ttl": ttl,
            "displayName": display_name,
        }
    )


def _coerce_tools(
    tools: Sequence[ToolDefinition | dict[str, Any]] | None,
) -> list[dict[str, Any]] | None:
    if not tools:
        return None
    function_definitions: list[ToolDefinition | dict[str, Any]] = []
    payloads: list[dict[str, Any]] = []
    for tool in tools:
        if isinstance(tool, ToolDefinition):
            function_definitions.append(tool)
        elif "functionDeclarations" in tool:
            if function_definitions:
                payloads.append(build_function_tool(function_definitions))
                function_definitions = []
            payloads.append(deepcopy(tool))
        else:
            if function_definitions:
                payloads.append(build_function_tool(function_definitions))
                function_definitions = []
            payloads.append(deepcopy(tool))
    if function_definitions:
        payloads.append(build_function_tool(function_definitions))
    return payloads
