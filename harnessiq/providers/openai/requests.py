"""OpenAI request payload builders."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal, Sequence

from harnessiq.providers.base import build_openai_style_messages, omit_none_values
from harnessiq.providers.openai.tools import build_function_tool, format_tool_definition
from harnessiq.shared.dtos import (
    OpenAIChatCompletionRequestDTO,
    OpenAIEmbeddingRequestDTO,
    OpenAIResponseInputMessageDTO,
    OpenAIResponseRequestDTO,
)
from harnessiq.shared.tools import ToolDefinition

ResponseRole = Literal["user", "assistant", "system", "developer"]


def build_request(
    request: OpenAIChatCompletionRequestDTO,
) -> dict[str, object]:
    """Build an OpenAI-style chat request body from canonical primitives."""
    return build_chat_completion_request(request)


def build_chat_completion_request(request: OpenAIChatCompletionRequestDTO) -> dict[str, object]:
    """Build a Chat Completions request body."""
    return omit_none_values(
        {
            "model": request.model_name,
            "messages": [message.to_dict() for message in build_openai_style_messages(request.system_prompt, request.messages)],
            "tools": _coerce_tool_payloads(request.tools, default_strict=False),
            "tool_choice": deepcopy(request.tool_choice) if isinstance(request.tool_choice, dict) else request.tool_choice,
            "response_format": deepcopy(request.response_format) if request.response_format is not None else None,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "parallel_tool_calls": request.parallel_tool_calls,
        }
    )


def build_response_input_text(text: str) -> dict[str, str]:
    """Build a Responses API text input part."""
    return {"type": "input_text", "text": text}


def build_response_input_image(
    image_url: str,
    *,
    detail: Literal["low", "high", "auto"] | None = None,
) -> dict[str, object]:
    """Build a Responses API image input part."""
    return omit_none_values(
        {
            "type": "input_image",
            "image_url": image_url,
            "detail": detail,
        }
    )


def build_response_input_file(
    *,
    file_id: str | None = None,
    filename: str | None = None,
    file_data: str | None = None,
) -> dict[str, object]:
    """Build a Responses API file input part."""
    return omit_none_values(
        {
            "type": "input_file",
            "file_id": file_id,
            "filename": filename,
            "file_data": file_data,
        }
    )


def build_response_input_message(
    role: ResponseRole,
    content: str | Sequence[dict[str, Any]],
) -> OpenAIResponseInputMessageDTO:
    """Build a Responses API input message."""
    if isinstance(content, str):
        normalized_content: list[dict[str, Any]] = [build_response_input_text(content)]
    else:
        normalized_content = [deepcopy(part) for part in content]
    return OpenAIResponseInputMessageDTO(role=role, content=tuple(normalized_content))


def build_json_schema_output(
    name: str,
    schema: dict[str, Any],
    *,
    description: str | None = None,
    strict: bool | None = None,
) -> dict[str, object]:
    """Build a JSON Schema structured-output payload."""
    return omit_none_values(
        {
            "type": "json_schema",
            "name": name,
            "description": description,
            "schema": deepcopy(schema),
            "strict": strict,
        }
    )


def build_response_text_config(
    *,
    format: dict[str, Any] | None = None,
    verbosity: Literal["low", "medium", "high"] | None = None,
) -> dict[str, object]:
    """Build Responses API text configuration."""
    return omit_none_values(
        {
            "format": deepcopy(format) if format is not None else None,
            "verbosity": verbosity,
        }
    )


def build_chat_response_format_json_schema(
    name: str,
    schema: dict[str, Any],
    *,
    description: str | None = None,
    strict: bool | None = None,
) -> dict[str, object]:
    """Build the Chat Completions response-format payload for structured outputs."""
    return {
        "type": "json_schema",
        "json_schema": build_json_schema_output(
            name,
            schema,
            description=description,
            strict=strict,
        ),
    }


def build_chat_response_format_json_object() -> dict[str, str]:
    """Build the Chat Completions response-format payload for JSON mode."""
    return {"type": "json_object"}


def build_response_request(request: OpenAIResponseRequestDTO) -> dict[str, object]:
    """Build a Responses API request body."""
    if isinstance(request.input_items, str):
        normalized_input: str | list[dict[str, Any]] = request.input_items
    else:
        normalized_input = [_serialize_input_item(item) for item in request.input_items]
    return omit_none_values(
        {
            "model": request.model_name,
            "input": normalized_input,
            "instructions": request.instructions,
            "tools": _coerce_tool_payloads(request.tools),
            "tool_choice": deepcopy(request.tool_choice) if isinstance(request.tool_choice, dict) else request.tool_choice,
            "text": deepcopy(request.text) if request.text is not None else None,
            "metadata": deepcopy(request.metadata) if request.metadata is not None else None,
            "temperature": request.temperature,
            "max_output_tokens": request.max_output_tokens,
            "parallel_tool_calls": request.parallel_tool_calls,
        }
    )


def build_embedding_request(request: OpenAIEmbeddingRequestDTO) -> dict[str, object]:
    """Build an embeddings request body."""
    if isinstance(request.input_value, str):
        normalized_input: str | list[Any] = request.input_value
    else:
        normalized_input = deepcopy(list(request.input_value))
    return omit_none_values(
        {
            "model": request.model_name,
            "input": normalized_input,
            "dimensions": request.dimensions,
            "encoding_format": request.encoding_format,
            "user": request.user,
        }
    )


def _serialize_input_item(item: Any) -> dict[str, Any]:
    if isinstance(item, OpenAIResponseInputMessageDTO):
        return item.to_dict()
    return deepcopy(item)


def _coerce_tool_payloads(
    tools: Sequence[ToolDefinition | dict[str, Any]] | None,
    *,
    default_strict: bool | None = None,
) -> list[dict[str, Any]] | None:
    if not tools:
        return None
    payloads: list[dict[str, Any]] = []
    for tool in tools:
        if isinstance(tool, ToolDefinition):
            if default_strict is None:
                payloads.append(format_tool_definition(tool))
            else:
                payloads.append(build_function_tool(tool, strict=default_strict))
        else:
            payloads.append(deepcopy(tool))
    return payloads
