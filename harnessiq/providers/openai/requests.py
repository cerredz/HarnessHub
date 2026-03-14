"""OpenAI request payload builders."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal, Sequence

from harnessiq.providers.base import build_openai_style_messages, omit_none_values
from harnessiq.providers.openai.tools import build_function_tool, format_tool_definition
from harnessiq.shared.providers import ProviderMessage
from harnessiq.shared.tools import ToolDefinition

ResponseRole = Literal["user", "assistant", "system", "developer"]


def build_request(
    model_name: str,
    system_prompt: str,
    messages: list[ProviderMessage],
    tools: list[ToolDefinition],
) -> dict[str, object]:
    """Build an OpenAI-style chat request body from canonical primitives."""
    return build_chat_completion_request(
        model_name=model_name,
        system_prompt=system_prompt,
        messages=messages,
        tools=tools,
    )


def build_chat_completion_request(
    *,
    model_name: str,
    system_prompt: str,
    messages: list[ProviderMessage],
    tools: Sequence[ToolDefinition | dict[str, Any]] | None = None,
    tool_choice: str | dict[str, Any] | None = None,
    response_format: dict[str, Any] | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    parallel_tool_calls: bool | None = None,
) -> dict[str, object]:
    """Build a Chat Completions request body."""
    return omit_none_values(
        {
            "model": model_name,
            "messages": build_openai_style_messages(system_prompt, messages),
            "tools": _coerce_tool_payloads(tools, default_strict=False),
            "tool_choice": deepcopy(tool_choice) if isinstance(tool_choice, dict) else tool_choice,
            "response_format": deepcopy(response_format) if response_format is not None else None,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "parallel_tool_calls": parallel_tool_calls,
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
) -> dict[str, object]:
    """Build a Responses API input message."""
    if isinstance(content, str):
        normalized_content: list[dict[str, Any]] = [build_response_input_text(content)]
    else:
        normalized_content = [deepcopy(part) for part in content]
    return {
        "role": role,
        "content": normalized_content,
    }


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


def build_response_request(
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
) -> dict[str, object]:
    """Build a Responses API request body."""
    if isinstance(input_items, str):
        normalized_input: str | list[dict[str, Any]] = input_items
    else:
        normalized_input = [deepcopy(item) for item in input_items]
    return omit_none_values(
        {
            "model": model_name,
            "input": normalized_input,
            "instructions": instructions,
            "tools": _coerce_tool_payloads(tools),
            "tool_choice": deepcopy(tool_choice) if isinstance(tool_choice, dict) else tool_choice,
            "text": deepcopy(text) if text is not None else None,
            "metadata": deepcopy(metadata) if metadata is not None else None,
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
            "parallel_tool_calls": parallel_tool_calls,
        }
    )


def build_embedding_request(
    *,
    model_name: str,
    input_value: str | Sequence[str] | Sequence[int] | Sequence[Sequence[int]],
    dimensions: int | None = None,
    encoding_format: Literal["float", "base64"] | None = None,
    user: str | None = None,
) -> dict[str, object]:
    """Build an embeddings request body."""
    if isinstance(input_value, str):
        normalized_input: str | list[Any] = input_value
    else:
        normalized_input = deepcopy(list(input_value))
    return omit_none_values(
        {
            "model": model_name,
            "input": normalized_input,
            "dimensions": dimensions,
            "encoding_format": encoding_format,
            "user": user,
        }
    )


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
