"""Anthropic message and token-count request builders."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal, Sequence

from harnessiq.providers.base import ProviderFormatError, normalize_messages, omit_none_values
from harnessiq.providers.anthropic.tools import format_tool_definition
from harnessiq.shared.dtos import AnthropicCountTokensRequestDTO, AnthropicMessageDTO, AnthropicMessageRequestDTO
from harnessiq.shared.tools import ToolDefinition

MessageRole = Literal["user", "assistant"]


def build_request(
    request: AnthropicCountTokensRequestDTO,
) -> dict[str, object]:
    """Build an Anthropic-style request body from canonical primitives."""
    return build_count_tokens_request(request)


def build_text_block(
    text: str,
    *,
    cache_control: dict[str, Any] | None = None,
) -> dict[str, object]:
    """Build an Anthropic text content block."""
    return omit_none_values(
        {
            "type": "text",
            "text": text,
            "cache_control": deepcopy(cache_control) if cache_control is not None else None,
        }
    )


def build_image_source(
    *,
    media_type: str,
    data: str,
    source_type: str = "base64",
) -> dict[str, str]:
    """Build the source payload for an Anthropic image block."""
    return {
        "type": source_type,
        "media_type": media_type,
        "data": data,
    }


def build_image_block(source: dict[str, Any]) -> dict[str, object]:
    """Build an Anthropic image content block."""
    return {"type": "image", "source": deepcopy(source)}


def build_tool_result_block(
    tool_use_id: str,
    content: str | Sequence[dict[str, Any]],
    *,
    is_error: bool | None = None,
) -> dict[str, object]:
    """Build an Anthropic tool-result block."""
    normalized_content = content if isinstance(content, str) else [deepcopy(part) for part in content]
    return omit_none_values(
        {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": normalized_content,
            "is_error": is_error,
        }
    )


def build_document_block(
    *,
    media_type: str,
    data: str,
    title: str | None = None,
    source_type: str = "base64",
) -> dict[str, object]:
    """Build an Anthropic document content block."""
    source = {
        "type": source_type,
        "media_type": media_type,
        "data": data,
    }
    return omit_none_values({"type": "document", "source": source, "title": title})


def build_message(
    role: MessageRole,
    content: str | Sequence[dict[str, Any]],
) -> AnthropicMessageDTO:
    """Build an Anthropic message item."""
    normalized_content: str | list[dict[str, Any]]
    if isinstance(content, str):
        normalized_content = content
    else:
        normalized_content = [deepcopy(part) for part in content]
    if isinstance(normalized_content, str):
        return AnthropicMessageDTO(role=role, content=normalized_content)
    return AnthropicMessageDTO(role=role, content=tuple(normalized_content))


def build_thinking_config(budget_tokens: int) -> dict[str, object]:
    """Build the Anthropic thinking configuration."""
    return {
        "type": "enabled",
        "budget_tokens": budget_tokens,
    }


def build_message_request(request: AnthropicMessageRequestDTO) -> dict[str, object]:
    """Build an Anthropic Messages API request body."""
    if request.system_prompt is None:
        normalized_system: str | list[dict[str, Any]] | None = None
    elif isinstance(request.system_prompt, str):
        normalized_system = request.system_prompt
    else:
        normalized_system = [deepcopy(part) for part in request.system_prompt]

    return omit_none_values(
        {
            "model": request.model_name,
            "system": normalized_system,
            "messages": [message.to_dict() for message in request.messages],
            "max_tokens": request.max_tokens,
            "tools": _coerce_tool_payloads(request.tools),
            "tool_choice": deepcopy(request.tool_choice) if request.tool_choice is not None else None,
            "thinking": deepcopy(request.thinking) if request.thinking is not None else None,
            "metadata": deepcopy(request.metadata) if request.metadata is not None else None,
            "stop_sequences": list(request.stop_sequences) if request.stop_sequences else None,
            "temperature": request.temperature,
            "mcp_servers": [deepcopy(server) for server in request.mcp_servers] if request.mcp_servers else None,
        }
    )


def build_count_tokens_request(request: AnthropicCountTokensRequestDTO) -> dict[str, object]:
    """Build an Anthropic token-count request body."""
    if request.system_prompt is None:
        normalized_system: str | list[dict[str, Any]] | None = None
    elif isinstance(request.system_prompt, str):
        normalized_system = request.system_prompt
    else:
        normalized_system = [deepcopy(part) for part in request.system_prompt]

    return omit_none_values(
        {
            "model": request.model_name,
            "system": normalized_system,
            "messages": [message.to_dict() for message in request.messages],
            "tools": _coerce_tool_payloads(request.tools),
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
            payloads.append(format_tool_definition(tool))
        else:
            payloads.append(deepcopy(tool))
    return payloads


def _normalize_message_items(messages: Sequence[AnthropicMessageDTO]) -> list[dict[str, Any]]:
    return [message.to_dict() for message in messages]
