"""Shared DTOs for provider-layer request and result boundaries."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Literal

from harnessiq.shared.dtos.base import SerializableDTO


def _coerce_mapping(mapping: Mapping[str, object] | None) -> dict[str, object]:
    if mapping is None:
        return {}
    return {str(key): deepcopy(value) for key, value in mapping.items()}


def _serialize_json_value(value: Any) -> Any:
    if isinstance(value, SerializableDTO):
        return deepcopy(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _serialize_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_serialize_json_value(item) for item in value]
    return deepcopy(value)


def _coerce_sequence(values: Sequence[Any] | None) -> tuple[Any, ...]:
    if values is None:
        return ()
    return tuple(deepcopy(value) for value in values)


def _coerce_string_sequence(values: Sequence[str] | None) -> tuple[str, ...]:
    if values is None:
        return ()
    return tuple(str(value) for value in values)


@dataclass(frozen=True, slots=True)
class ProviderMessageDTO(SerializableDTO):
    """Canonical provider-agnostic message DTO."""

    role: Literal["system", "user", "assistant"]
    content: str

    def __post_init__(self) -> None:
        normalized_role = self.role.strip().lower()
        if normalized_role not in {"system", "user", "assistant"}:
            raise ValueError(f"Unsupported provider message role '{self.role}'.")
        normalized_content = self.content.strip()
        if not normalized_content:
            raise ValueError("Provider message content must not be blank.")
        object.__setattr__(self, "role", normalized_role)
        object.__setattr__(self, "content", normalized_content)

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass(frozen=True, slots=True)
class OpenAIResponseInputMessageDTO(SerializableDTO):
    """Responses API message item DTO."""

    role: Literal["user", "assistant", "system", "developer"]
    content: tuple[Any, ...]

    def __post_init__(self) -> None:
        normalized_role = self.role.strip().lower()
        if normalized_role not in {"user", "assistant", "system", "developer"}:
            raise ValueError(f"Unsupported OpenAI response message role '{self.role}'.")
        if not self.content:
            raise ValueError("OpenAI response message content must not be empty.")
        object.__setattr__(self, "role", normalized_role)
        object.__setattr__(self, "content", _coerce_sequence(self.content))

    def to_dict(self) -> dict[str, object]:
        return {
            "role": self.role,
            "content": [_serialize_json_value(part) for part in self.content],
        }


@dataclass(frozen=True, slots=True)
class OpenAIChatCompletionRequestDTO(SerializableDTO):
    """Public DTO for OpenAI chat-completions requests."""

    model_name: str
    system_prompt: str
    messages: tuple[ProviderMessageDTO, ...]
    tools: tuple[Any, ...] = field(default_factory=tuple)
    tool_choice: str | Mapping[str, Any] | None = None
    response_format: SerializableDTO | Mapping[str, Any] | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    parallel_tool_calls: bool | None = None

    def __post_init__(self) -> None:
        normalized_model_name = self.model_name.strip()
        if not normalized_model_name:
            raise ValueError("OpenAI chat request model_name must not be blank.")
        object.__setattr__(self, "model_name", normalized_model_name)
        object.__setattr__(self, "messages", tuple(deepcopy(message) for message in self.messages))
        object.__setattr__(self, "tools", _coerce_sequence(self.tools))
        object.__setattr__(self, "response_format", deepcopy(self.response_format))

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "model_name": self.model_name,
            "system_prompt": self.system_prompt,
            "messages": [message.to_dict() for message in self.messages],
        }
        if self.tools:
            payload["tools"] = [_serialize_json_value(tool) for tool in self.tools]
        if self.tool_choice is not None:
            payload["tool_choice"] = _serialize_json_value(self.tool_choice)
        if self.response_format is not None:
            payload["response_format"] = _serialize_json_value(self.response_format)
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        if self.parallel_tool_calls is not None:
            payload["parallel_tool_calls"] = self.parallel_tool_calls
        return payload


@dataclass(frozen=True, slots=True)
class OpenAIResponseRequestDTO(SerializableDTO):
    """Public DTO for OpenAI Responses API requests."""

    model_name: str
    input_items: str | tuple[Any, ...]
    instructions: str | None = None
    tools: tuple[Any, ...] = field(default_factory=tuple)
    tool_choice: str | Mapping[str, Any] | None = None
    text: SerializableDTO | Mapping[str, Any] | None = None
    metadata: dict[str, str] | None = None
    temperature: float | None = None
    max_output_tokens: int | None = None
    parallel_tool_calls: bool | None = None

    def __post_init__(self) -> None:
        normalized_model_name = self.model_name.strip()
        if not normalized_model_name:
            raise ValueError("OpenAI response request model_name must not be blank.")
        object.__setattr__(self, "model_name", normalized_model_name)
        if not isinstance(self.input_items, str):
            object.__setattr__(self, "input_items", _coerce_sequence(self.input_items))
        object.__setattr__(self, "tools", _coerce_sequence(self.tools))
        object.__setattr__(self, "text", deepcopy(self.text))
        if self.metadata is not None:
            object.__setattr__(self, "metadata", {str(key): str(value) for key, value in self.metadata.items()})

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {"model_name": self.model_name}
        if isinstance(self.input_items, str):
            payload["input_items"] = self.input_items
        else:
            payload["input_items"] = [_serialize_json_value(item) for item in self.input_items]
        if self.instructions is not None:
            payload["instructions"] = self.instructions
        if self.tools:
            payload["tools"] = [_serialize_json_value(tool) for tool in self.tools]
        if self.tool_choice is not None:
            payload["tool_choice"] = _serialize_json_value(self.tool_choice)
        if self.text is not None:
            payload["text"] = _serialize_json_value(self.text)
        if self.metadata is not None:
            payload["metadata"] = dict(self.metadata)
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        if self.max_output_tokens is not None:
            payload["max_output_tokens"] = self.max_output_tokens
        if self.parallel_tool_calls is not None:
            payload["parallel_tool_calls"] = self.parallel_tool_calls
        return payload


@dataclass(frozen=True, slots=True)
class OpenAIEmbeddingRequestDTO(SerializableDTO):
    """Public DTO for OpenAI embeddings requests."""

    model_name: str
    input_value: str | tuple[Any, ...]
    dimensions: int | None = None
    encoding_format: Literal["float", "base64"] | None = None
    user: str | None = None

    def __post_init__(self) -> None:
        normalized_model_name = self.model_name.strip()
        if not normalized_model_name:
            raise ValueError("OpenAI embedding request model_name must not be blank.")
        object.__setattr__(self, "model_name", normalized_model_name)
        if not isinstance(self.input_value, str):
            object.__setattr__(self, "input_value", _coerce_sequence(self.input_value))
        if self.user is not None:
            object.__setattr__(self, "user", self.user.strip() or None)

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {"model_name": self.model_name}
        payload["input_value"] = _serialize_json_value(self.input_value)
        if self.dimensions is not None:
            payload["dimensions"] = self.dimensions
        if self.encoding_format is not None:
            payload["encoding_format"] = self.encoding_format
        if self.user is not None:
            payload["user"] = self.user
        return payload


@dataclass(frozen=True, slots=True)
class AnthropicMessageDTO(SerializableDTO):
    """Anthropic Messages API message DTO."""

    role: Literal["user", "assistant"]
    content: str | tuple[Any, ...]

    def __post_init__(self) -> None:
        normalized_role = self.role.strip().lower()
        if normalized_role not in {"user", "assistant"}:
            raise ValueError(f"Unsupported Anthropic message role '{self.role}'.")
        object.__setattr__(self, "role", normalized_role)
        if not isinstance(self.content, str):
            object.__setattr__(self, "content", _coerce_sequence(self.content))

    def to_dict(self) -> dict[str, object]:
        if isinstance(self.content, str):
            content: object = self.content
        else:
            content = [_serialize_json_value(part) for part in self.content]
        return {"role": self.role, "content": content}


@dataclass(frozen=True, slots=True)
class AnthropicMessageRequestDTO(SerializableDTO):
    """Public DTO for Anthropic Messages API calls."""

    model_name: str
    messages: tuple[AnthropicMessageDTO, ...]
    max_tokens: int
    system_prompt: str | tuple[Any, ...] | None = None
    tools: tuple[Any, ...] = field(default_factory=tuple)
    tool_choice: Mapping[str, Any] | None = None
    thinking: SerializableDTO | Mapping[str, Any] | None = None
    metadata: dict[str, str] | None = None
    stop_sequences: tuple[str, ...] = field(default_factory=tuple)
    temperature: float | None = None
    mcp_servers: tuple[Any, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        normalized_model_name = self.model_name.strip()
        if not normalized_model_name:
            raise ValueError("Anthropic message request model_name must not be blank.")
        object.__setattr__(self, "model_name", normalized_model_name)
        object.__setattr__(self, "messages", tuple(deepcopy(message) for message in self.messages))
        if self.system_prompt is not None and not isinstance(self.system_prompt, str):
            object.__setattr__(self, "system_prompt", _coerce_sequence(self.system_prompt))
        object.__setattr__(self, "tools", _coerce_sequence(self.tools))
        object.__setattr__(self, "thinking", deepcopy(self.thinking))
        object.__setattr__(self, "stop_sequences", _coerce_string_sequence(self.stop_sequences))
        object.__setattr__(self, "mcp_servers", _coerce_sequence(self.mcp_servers))
        if self.metadata is not None:
            object.__setattr__(self, "metadata", {str(key): str(value) for key, value in self.metadata.items()})

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "model_name": self.model_name,
            "messages": [message.to_dict() for message in self.messages],
            "max_tokens": self.max_tokens,
        }
        if self.system_prompt is not None:
            payload["system_prompt"] = _serialize_json_value(self.system_prompt)
        if self.tools:
            payload["tools"] = [_serialize_json_value(tool) for tool in self.tools]
        if self.tool_choice is not None:
            payload["tool_choice"] = _serialize_json_value(self.tool_choice)
        if self.thinking is not None:
            payload["thinking"] = _serialize_json_value(self.thinking)
        if self.metadata is not None:
            payload["metadata"] = dict(self.metadata)
        if self.stop_sequences:
            payload["stop_sequences"] = list(self.stop_sequences)
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        if self.mcp_servers:
            payload["mcp_servers"] = [_serialize_json_value(server) for server in self.mcp_servers]
        return payload


@dataclass(frozen=True, slots=True)
class AnthropicCountTokensRequestDTO(SerializableDTO):
    """Public DTO for Anthropic count-tokens calls."""

    model_name: str
    messages: tuple[AnthropicMessageDTO, ...]
    system_prompt: str | tuple[Any, ...] | None = None
    tools: tuple[Any, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        normalized_model_name = self.model_name.strip()
        if not normalized_model_name:
            raise ValueError("Anthropic count-tokens request model_name must not be blank.")
        object.__setattr__(self, "model_name", normalized_model_name)
        object.__setattr__(self, "messages", tuple(deepcopy(message) for message in self.messages))
        if self.system_prompt is not None and not isinstance(self.system_prompt, str):
            object.__setattr__(self, "system_prompt", _coerce_sequence(self.system_prompt))
        object.__setattr__(self, "tools", _coerce_sequence(self.tools))

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "model_name": self.model_name,
            "messages": [message.to_dict() for message in self.messages],
        }
        if self.system_prompt is not None:
            payload["system_prompt"] = _serialize_json_value(self.system_prompt)
        if self.tools:
            payload["tools"] = [_serialize_json_value(tool) for tool in self.tools]
        return payload


@dataclass(frozen=True, slots=True)
class GeminiContentDTO(SerializableDTO):
    """Gemini content item DTO."""

    role: Literal["user", "model"]
    parts: tuple[Any, ...]

    def __post_init__(self) -> None:
        normalized_role = self.role.strip().lower()
        if normalized_role not in {"user", "model"}:
            raise ValueError(f"Unsupported Gemini content role '{self.role}'.")
        if not self.parts:
            raise ValueError("Gemini content parts must not be empty.")
        object.__setattr__(self, "role", normalized_role)
        object.__setattr__(self, "parts", _coerce_sequence(self.parts))

    def to_dict(self) -> dict[str, object]:
        return {"role": self.role, "parts": [_serialize_json_value(part) for part in self.parts]}


@dataclass(frozen=True, slots=True)
class GeminiSystemInstructionDTO(SerializableDTO):
    """Gemini system instruction DTO."""

    parts: tuple[Any, ...]

    def __post_init__(self) -> None:
        if not self.parts:
            raise ValueError("Gemini system instruction parts must not be empty.")
        object.__setattr__(self, "parts", _coerce_sequence(self.parts))

    def to_dict(self) -> dict[str, object]:
        return {"parts": [_serialize_json_value(part) for part in self.parts]}


@dataclass(frozen=True, slots=True)
class GeminiGenerationConfigDTO(SerializableDTO):
    """Gemini generation configuration DTO."""

    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    max_output_tokens: int | None = None
    response_mime_type: str | None = None
    response_schema: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "response_schema", _coerce_mapping(self.response_schema))

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {}
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        if self.top_p is not None:
            payload["topP"] = self.top_p
        if self.top_k is not None:
            payload["topK"] = self.top_k
        if self.max_output_tokens is not None:
            payload["maxOutputTokens"] = self.max_output_tokens
        if self.response_mime_type is not None:
            payload["responseMimeType"] = self.response_mime_type
        if self.response_schema:
            payload["responseSchema"] = _serialize_json_value(self.response_schema)
        return payload


@dataclass(frozen=True, slots=True)
class GeminiGenerateContentRequestDTO(SerializableDTO):
    """Public DTO for Gemini generate-content calls."""

    model_name: str
    contents: tuple[GeminiContentDTO, ...]
    system_instruction: GeminiSystemInstructionDTO | Mapping[str, Any] | None = None
    tools: tuple[Any, ...] = field(default_factory=tuple)
    tool_config: Mapping[str, Any] | None = None
    generation_config: SerializableDTO | Mapping[str, Any] | None = None
    cached_content: str | None = None

    def __post_init__(self) -> None:
        normalized_model_name = self.model_name.strip()
        if not normalized_model_name:
            raise ValueError("Gemini generate-content request model_name must not be blank.")
        object.__setattr__(self, "model_name", normalized_model_name)
        object.__setattr__(self, "contents", tuple(deepcopy(content) for content in self.contents))
        object.__setattr__(self, "tools", _coerce_sequence(self.tools))
        object.__setattr__(self, "generation_config", deepcopy(self.generation_config))
        if self.cached_content is not None:
            object.__setattr__(self, "cached_content", self.cached_content.strip() or None)

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "model_name": self.model_name,
            "contents": [content.to_dict() for content in self.contents],
        }
        if self.system_instruction is not None:
            payload["system_instruction"] = _serialize_json_value(self.system_instruction)
        if self.tools:
            payload["tools"] = [_serialize_json_value(tool) for tool in self.tools]
        if self.tool_config is not None:
            payload["tool_config"] = _serialize_json_value(self.tool_config)
        if self.generation_config is not None:
            payload["generation_config"] = _serialize_json_value(self.generation_config)
        if self.cached_content is not None:
            payload["cached_content"] = self.cached_content
        return payload


@dataclass(frozen=True, slots=True)
class GeminiCountTokensRequestDTO(SerializableDTO):
    """Public DTO for Gemini count-tokens calls."""

    model_name: str
    contents: tuple[GeminiContentDTO, ...]
    system_instruction: GeminiSystemInstructionDTO | Mapping[str, Any] | None = None
    tools: tuple[Any, ...] = field(default_factory=tuple)
    tool_config: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        normalized_model_name = self.model_name.strip()
        if not normalized_model_name:
            raise ValueError("Gemini count-tokens request model_name must not be blank.")
        object.__setattr__(self, "model_name", normalized_model_name)
        object.__setattr__(self, "contents", tuple(deepcopy(content) for content in self.contents))
        object.__setattr__(self, "tools", _coerce_sequence(self.tools))

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "model_name": self.model_name,
            "contents": [content.to_dict() for content in self.contents],
        }
        if self.system_instruction is not None:
            payload["system_instruction"] = _serialize_json_value(self.system_instruction)
        if self.tools:
            payload["tools"] = [_serialize_json_value(tool) for tool in self.tools]
        if self.tool_config is not None:
            payload["tool_config"] = _serialize_json_value(self.tool_config)
        return payload


@dataclass(frozen=True, slots=True)
class GeminiCacheCreateRequestDTO(SerializableDTO):
    """Public DTO for Gemini cached-content creation calls."""

    model_name: str
    contents: tuple[GeminiContentDTO, ...]
    system_instruction: GeminiSystemInstructionDTO | Mapping[str, Any] | None = None
    tools: tuple[Any, ...] = field(default_factory=tuple)
    ttl: str | None = None
    display_name: str | None = None

    def __post_init__(self) -> None:
        normalized_model_name = self.model_name.strip()
        if not normalized_model_name:
            raise ValueError("Gemini cache request model_name must not be blank.")
        object.__setattr__(self, "model_name", normalized_model_name)
        object.__setattr__(self, "contents", tuple(deepcopy(content) for content in self.contents))
        object.__setattr__(self, "tools", _coerce_sequence(self.tools))
        if self.ttl is not None:
            object.__setattr__(self, "ttl", self.ttl.strip() or None)
        if self.display_name is not None:
            object.__setattr__(self, "display_name", self.display_name.strip() or None)

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "model_name": self.model_name,
            "contents": [content.to_dict() for content in self.contents],
        }
        if self.system_instruction is not None:
            payload["system_instruction"] = _serialize_json_value(self.system_instruction)
        if self.tools:
            payload["tools"] = [_serialize_json_value(tool) for tool in self.tools]
        if self.ttl is not None:
            payload["ttl"] = self.ttl
        if self.display_name is not None:
            payload["display_name"] = self.display_name
        return payload


@dataclass(frozen=True, slots=True)
class GrokSearchParametersDTO(SerializableDTO):
    """xAI search parameter DTO."""

    mode: Literal["auto", "on", "off"] | None = None
    max_search_results: int | None = None
    return_citations: bool | None = None
    from_date: str | None = None
    to_date: str | None = None
    sources: tuple[Literal["web", "x"], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "sources", tuple(self.sources))

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {}
        if self.mode is not None:
            payload["mode"] = self.mode
        if self.max_search_results is not None:
            payload["max_search_results"] = self.max_search_results
        if self.return_citations is not None:
            payload["return_citations"] = self.return_citations
        if self.from_date is not None:
            payload["from_date"] = self.from_date
        if self.to_date is not None:
            payload["to_date"] = self.to_date
        if self.sources:
            payload["sources"] = list(self.sources)
        return payload


@dataclass(frozen=True, slots=True)
class GrokChatCompletionRequestDTO(SerializableDTO):
    """Public DTO for Grok chat-completions requests."""

    model_name: str
    system_prompt: str
    messages: tuple[ProviderMessageDTO, ...]
    tools: tuple[Any, ...] = field(default_factory=tuple)
    tool_choice: str | Mapping[str, Any] | None = None
    response_format: SerializableDTO | Mapping[str, Any] | None = None
    search_parameters: SerializableDTO | Mapping[str, Any] | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    reasoning_effort: Literal["low", "medium", "high"] | None = None

    def __post_init__(self) -> None:
        normalized_model_name = self.model_name.strip()
        if not normalized_model_name:
            raise ValueError("Grok chat request model_name must not be blank.")
        object.__setattr__(self, "model_name", normalized_model_name)
        object.__setattr__(self, "messages", tuple(deepcopy(message) for message in self.messages))
        object.__setattr__(self, "tools", _coerce_sequence(self.tools))
        object.__setattr__(self, "response_format", deepcopy(self.response_format))
        object.__setattr__(self, "search_parameters", deepcopy(self.search_parameters))

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "model_name": self.model_name,
            "system_prompt": self.system_prompt,
            "messages": [message.to_dict() for message in self.messages],
        }
        if self.tools:
            payload["tools"] = [_serialize_json_value(tool) for tool in self.tools]
        if self.tool_choice is not None:
            payload["tool_choice"] = _serialize_json_value(self.tool_choice)
        if self.response_format is not None:
            payload["response_format"] = _serialize_json_value(self.response_format)
        if self.search_parameters is not None:
            payload["search_parameters"] = _serialize_json_value(self.search_parameters)
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        if self.reasoning_effort is not None:
            payload["reasoning_effort"] = self.reasoning_effort
        return payload


@dataclass(frozen=True, slots=True)
class ProviderOperationRequestDTO(SerializableDTO):
    """Public DTO for prepared-request provider client calls."""

    operation: str
    path_params: dict[str, object] = field(default_factory=dict)
    query: dict[str, object] = field(default_factory=dict)
    payload: Any | None = None
    run_id: str | None = None

    def __post_init__(self) -> None:
        normalized_operation = self.operation.strip()
        if not normalized_operation:
            raise ValueError("Provider operation must not be blank.")
        object.__setattr__(self, "operation", normalized_operation)
        object.__setattr__(self, "path_params", _coerce_mapping(self.path_params))
        object.__setattr__(self, "query", _coerce_mapping(self.query))
        object.__setattr__(self, "payload", deepcopy(self.payload))
        if self.run_id is not None:
            normalized_run_id = self.run_id.strip()
            object.__setattr__(self, "run_id", normalized_run_id or None)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"operation": self.operation}
        if self.path_params:
            payload["path_params"] = deepcopy(self.path_params)
        if self.query:
            payload["query"] = deepcopy(self.query)
        if self.payload is not None:
            payload["payload"] = deepcopy(self.payload)
        if self.run_id is not None:
            payload["run_id"] = self.run_id
        return payload


@dataclass(frozen=True, slots=True)
class PreparedProviderOperationResultDTO(SerializableDTO):
    """Public DTO for prepared-request provider execution results."""

    operation: str
    method: str
    path: str
    response: Any

    def __post_init__(self) -> None:
        object.__setattr__(self, "operation", self.operation.strip())
        object.__setattr__(self, "method", self.method.strip())
        object.__setattr__(self, "path", self.path.strip())
        object.__setattr__(self, "response", deepcopy(self.response))

    @classmethod
    def from_prepared_request(
        cls,
        *,
        prepared: Any,
        response: Any,
    ) -> "PreparedProviderOperationResultDTO":
        return cls(
            operation=str(prepared.operation.name),
            method=str(prepared.method),
            path=str(prepared.path),
            response=response,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "method": self.method,
            "path": self.path,
            "response": deepcopy(self.response),
        }


@dataclass(frozen=True, slots=True)
class ProviderPayloadRequestDTO(SerializableDTO):
    """Public DTO for payload-dispatch provider tool and client calls."""

    operation: str
    payload: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized_operation = self.operation.strip()
        if not normalized_operation:
            raise ValueError("Provider operation must not be blank.")
        object.__setattr__(self, "operation", normalized_operation)
        object.__setattr__(self, "payload", _coerce_mapping(self.payload))

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"operation": self.operation}
        if self.payload:
            payload["payload"] = deepcopy(self.payload)
        return payload


@dataclass(frozen=True, slots=True)
class ProviderPayloadResultDTO(SerializableDTO):
    """Public DTO for payload-dispatch provider execution results."""

    operation: str
    result: Any

    def __post_init__(self) -> None:
        object.__setattr__(self, "operation", self.operation.strip())
        object.__setattr__(self, "result", deepcopy(self.result))

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "result": deepcopy(self.result),
        }


@dataclass(frozen=True, slots=True)
class ArxivOperationResultDTO(SerializableDTO):
    """Public DTO for arXiv tool/client result envelopes."""

    operation: str
    result_fields: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized_operation = self.operation.strip()
        if not normalized_operation:
            raise ValueError("Provider operation must not be blank.")
        object.__setattr__(self, "operation", normalized_operation)
        object.__setattr__(self, "result_fields", _coerce_mapping(self.result_fields))

    @classmethod
    def from_search(cls, *, results: list[dict[str, Any]]) -> "ArxivOperationResultDTO":
        return cls(operation="search", result_fields={"results": results, "count": len(results)})

    @classmethod
    def from_search_raw(cls, *, xml: str) -> "ArxivOperationResultDTO":
        return cls(operation="search_raw", result_fields={"xml": xml})

    @classmethod
    def from_get_paper(cls, *, paper: dict[str, Any] | None) -> "ArxivOperationResultDTO":
        return cls(operation="get_paper", result_fields={"paper": paper})

    @classmethod
    def from_download_paper(cls, *, saved_to: str) -> "ArxivOperationResultDTO":
        return cls(operation="download_paper", result_fields={"saved_to": saved_to})

    def to_dict(self) -> dict[str, Any]:
        payload = {"operation": self.operation}
        payload.update(deepcopy(self.result_fields))
        return payload


__all__ = [
    "AnthropicCountTokensRequestDTO",
    "AnthropicMessageDTO",
    "AnthropicMessageRequestDTO",
    "ArxivOperationResultDTO",
    "GeminiCacheCreateRequestDTO",
    "GeminiContentDTO",
    "GeminiCountTokensRequestDTO",
    "GeminiGenerateContentRequestDTO",
    "GeminiGenerationConfigDTO",
    "GeminiSystemInstructionDTO",
    "GrokChatCompletionRequestDTO",
    "GrokSearchParametersDTO",
    "OpenAIChatCompletionRequestDTO",
    "OpenAIEmbeddingRequestDTO",
    "OpenAIResponseInputMessageDTO",
    "OpenAIResponseRequestDTO",
    "PreparedProviderOperationResultDTO",
    "ProviderMessageDTO",
    "ProviderOperationRequestDTO",
    "ProviderPayloadRequestDTO",
    "ProviderPayloadResultDTO",
]
