"""Gemini content, generation-config, and caching builders."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal, Sequence

from harnessiq.providers.base import build_gemini_contents, omit_none_values
from harnessiq.providers.gemini.tools import build_function_tool
from harnessiq.shared.dtos import (
    GeminiCacheCreateRequestDTO,
    GeminiContentDTO,
    GeminiCountTokensRequestDTO,
    GeminiGenerateContentRequestDTO,
    GeminiGenerationConfigDTO,
    GeminiSystemInstructionDTO,
    ProviderMessageDTO,
)
from harnessiq.shared.tools import ToolDefinition

ContentRole = Literal["user", "model"]


def build_request(
    model_name: str,
    system_prompt: str,
    messages: list[ProviderMessageDTO],
    tools: list[ToolDefinition],
) -> dict[str, object]:
    """Build a Gemini-style compatibility request body from canonical primitives."""
    request: dict[str, object] = {
        "model": model_name,
        "contents": [content.to_dict() for content in build_gemini_contents(messages)],
    }
    if system_prompt:
        request["system_instruction"] = GeminiSystemInstructionDTO(parts=({"text": system_prompt},)).to_dict()
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
) -> GeminiContentDTO:
    """Build a Gemini content item."""
    return GeminiContentDTO(role=role, parts=tuple(deepcopy(part) for part in parts))


def build_system_instruction(parts: str | Sequence[dict[str, Any]]) -> GeminiSystemInstructionDTO:
    """Build the Gemini system-instruction payload."""
    if isinstance(parts, str):
        normalized_parts = [build_text_part(parts)]
    else:
        normalized_parts = [deepcopy(part) for part in parts]
    return GeminiSystemInstructionDTO(parts=tuple(normalized_parts))


def build_generation_config(
    *,
    temperature: float | None = None,
    top_p: float | None = None,
    top_k: int | None = None,
    max_output_tokens: int | None = None,
    response_mime_type: str | None = None,
    response_schema: dict[str, Any] | None = None,
) -> GeminiGenerationConfigDTO:
    """Build Gemini generation configuration."""
    return GeminiGenerationConfigDTO(
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        max_output_tokens=max_output_tokens,
        response_mime_type=response_mime_type,
        response_schema=deepcopy(response_schema) if response_schema is not None else None,
    )


def build_generate_content_request(request: GeminiGenerateContentRequestDTO) -> dict[str, object]:
    """Build a Gemini generate-content request body."""
    return omit_none_values(
        {
            "contents": [content.to_dict() for content in request.contents],
            "systemInstruction": request.system_instruction.to_dict() if isinstance(request.system_instruction, GeminiSystemInstructionDTO) else deepcopy(request.system_instruction),
            "tools": _coerce_tools(request.tools),
            "toolConfig": deepcopy(request.tool_config) if request.tool_config is not None else None,
            "generationConfig": request.generation_config.to_dict() if isinstance(request.generation_config, GeminiGenerationConfigDTO) else deepcopy(request.generation_config),
            "cachedContent": request.cached_content,
        }
    )


def build_count_tokens_request(request: GeminiCountTokensRequestDTO) -> dict[str, object]:
    """Build a Gemini count-tokens request body."""
    return omit_none_values(
        {
            "contents": [content.to_dict() for content in request.contents],
            "systemInstruction": request.system_instruction.to_dict() if isinstance(request.system_instruction, GeminiSystemInstructionDTO) else deepcopy(request.system_instruction),
            "tools": _coerce_tools(request.tools),
            "toolConfig": deepcopy(request.tool_config) if request.tool_config is not None else None,
        }
    )


def build_cached_content_request(request: GeminiCacheCreateRequestDTO) -> dict[str, object]:
    """Build a Gemini cached-content create request body."""
    return omit_none_values(
        {
            "model": request.model_name,
            "contents": [content.to_dict() for content in request.contents],
            "systemInstruction": request.system_instruction.to_dict() if isinstance(request.system_instruction, GeminiSystemInstructionDTO) else deepcopy(request.system_instruction),
            "tools": _coerce_tools(request.tools),
            "ttl": request.ttl,
            "displayName": request.display_name,
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
