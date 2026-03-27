"""First-class provider-backed AgentModel adapters."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping, Sequence
from typing import Any, cast

from harnessiq.config import ModelProfile
from harnessiq.interfaces import AnthropicModelClient, GeminiModelClient, OpenAIStyleModelClient
from harnessiq.providers import trace_model_call
from harnessiq.providers.anthropic import AnthropicClient
from harnessiq.providers.gemini import (
    GeminiClient,
    build_function_calling_config,
    build_generation_config,
    build_system_instruction,
    build_tool_config,
)
from harnessiq.providers.grok import GrokClient
from harnessiq.providers.openai import OpenAIClient
from harnessiq.shared.agents import AgentModelRequest, AgentModelResponse
from harnessiq.shared.dtos import (
    AnthropicMessageDTO,
    AnthropicMessageRequestDTO,
    GeminiContentDTO,
    GeminiGenerateContentRequestDTO,
    GrokChatCompletionRequestDTO,
    OpenAIChatCompletionRequestDTO,
    ProviderMessageDTO,
)
from harnessiq.shared.providers import SUPPORTED_PROVIDERS
from harnessiq.shared.tools import ToolCall, ToolDefinition

DEFAULT_ANTHROPIC_MAX_OUTPUT_TOKENS = 4096
DEFAULT_GROK_MODEL = "grok-4-1-fast-reasoning"
_SUPPORTED_PROVIDER_NAMES = frozenset(SUPPORTED_PROVIDERS)
_ProviderModelClient = OpenAIStyleModelClient | AnthropicModelClient | GeminiModelClient


class ProviderAgentModel:
    """Shared `AgentModel` implementation backed by one provider client."""

    def __init__(
        self,
        *,
        provider: str,
        model_name: str,
        client: _ProviderModelClient,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        reasoning_effort: str | None = None,
        project_name: str | None = None,
        tracing_enabled: bool = True,
    ) -> None:
        normalized_provider = normalize_model_provider(provider)
        normalized_model_name = model_name.strip()
        if not normalized_model_name:
            raise ValueError("model_name must not be blank.")
        if isinstance(temperature, bool):
            raise ValueError("temperature must be numeric when provided.")
        if max_output_tokens is not None and (isinstance(max_output_tokens, bool) or max_output_tokens <= 0):
            raise ValueError("max_output_tokens must be greater than zero when provided.")
        self._provider_name = normalized_provider
        self._model_name = normalized_model_name
        self._client = client
        self._temperature = float(temperature) if temperature is not None else None
        self._max_output_tokens = int(max_output_tokens) if max_output_tokens is not None else None
        self._reasoning_effort = reasoning_effort.strip() if isinstance(reasoning_effort, str) and reasoning_effort.strip() else None
        self._project_name = project_name.strip() if isinstance(project_name, str) and project_name.strip() else None
        self._tracing_enabled = tracing_enabled
        self._name_to_key: dict[str, str] = {}

    @property
    def provider(self) -> str:
        return self._provider_name

    @property
    def model_name(self) -> str:
        return self._model_name

    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        self._name_to_key = {tool.name: tool.key for tool in request.tools}
        messages = build_provider_messages(request)
        tools = list(request.tools)
        return self._generate_provider_turn(
            request=request,
            messages=messages,
            tools=tools,
        )

    def generate_turn_with_override(
        self,
        request: AgentModelRequest,
        model_name: str,
    ) -> AgentModelResponse:
        return self.with_model_override(model_name).generate_turn(request)

    def with_model_override(self, model_name: str) -> "ProviderAgentModel":
        raise NotImplementedError("Subclasses must implement with_model_override().")

    def _generate_provider_turn(
        self,
        *,
        request: AgentModelRequest,
        messages: list[ProviderMessageDTO],
        tools: list[ToolDefinition],
    ) -> AgentModelResponse:
        provider = self._provider_name
        if provider == "openai":
            return self._generate_openai_turn(request=request, messages=messages, tools=tools)
        if provider == "anthropic":
            return self._generate_anthropic_turn(request=request, messages=messages, tools=tools)
        if provider == "gemini":
            return self._generate_gemini_turn(request=request, messages=messages, tools=tools)
        if provider == "grok":
            return self._generate_grok_turn(request=request, messages=messages, tools=tools)
        raise ValueError(f"Unsupported provider '{provider}'.")

    def _openai_style_client(self) -> OpenAIStyleModelClient:
        return cast(OpenAIStyleModelClient, self._client)

    def _anthropic_client(self) -> AnthropicModelClient:
        return cast(AnthropicModelClient, self._client)

    def _gemini_client(self) -> GeminiModelClient:
        return cast(GeminiModelClient, self._client)

    def _generate_openai_turn(
        self,
        *,
        request: AgentModelRequest,
        messages: list[ProviderMessageDTO],
        tools: list[ToolDefinition],
    ) -> AgentModelResponse:
        client = self._openai_style_client()
        provider_request = OpenAIChatCompletionRequestDTO(
            model_name=self._model_name,
            system_prompt=request.system_prompt,
            messages=tuple(messages),
            tools=tuple(tools),
            max_tokens=self._max_output_tokens,
            temperature=self._temperature,
            parallel_tool_calls=True if tools else None,
        )
        raw = trace_model_call(
            lambda: client.create_chat_completion(provider_request),
            provider="openai",
            model_name=self._model_name,
            system_prompt=request.system_prompt,
            messages=messages,
            tools=tools,
            request_payload=provider_request.to_dict(),
            project_name=self._project_name,
            enabled=self._tracing_enabled or None,
        )
        return self._parse_openai_style_response(raw)

    def _generate_anthropic_turn(
        self,
        *,
        request: AgentModelRequest,
        messages: list[ProviderMessageDTO],
        tools: list[ToolDefinition],
    ) -> AgentModelResponse:
        client = self._anthropic_client()
        provider_request = AnthropicMessageRequestDTO(
            model_name=self._model_name,
            messages=tuple(
                AnthropicMessageDTO(role=message.role, content=message.content) for message in messages if message.role != "system"
            ),
            max_tokens=self._max_output_tokens or DEFAULT_ANTHROPIC_MAX_OUTPUT_TOKENS,
            system_prompt=request.system_prompt or None,
            tools=tuple(tools),
            tool_choice={"type": "auto"} if tools else None,
            temperature=self._temperature,
        )
        raw = trace_model_call(
            lambda: client.create_message(provider_request),
            provider="anthropic",
            model_name=self._model_name,
            system_prompt=request.system_prompt,
            messages=messages,
            tools=tools,
            request_payload=provider_request.to_dict(),
            project_name=self._project_name,
            enabled=self._tracing_enabled or None,
        )
        return self._parse_anthropic_response(raw)

    def _generate_gemini_turn(
        self,
        *,
        request: AgentModelRequest,
        messages: list[ProviderMessageDTO],
        tools: list[ToolDefinition],
    ) -> AgentModelResponse:
        generation_config = build_generation_config(
            temperature=self._temperature,
            max_output_tokens=self._max_output_tokens,
        )
        client = self._gemini_client()
        provider_request = GeminiGenerateContentRequestDTO(
            model_name=self._model_name,
            contents=tuple(_build_gemini_contents(messages)),
            system_instruction=build_system_instruction(request.system_prompt) if request.system_prompt else None,
            tools=tuple(tools),
            tool_config=(
                build_tool_config(function_calling_config=build_function_calling_config(mode="AUTO"))
                if tools
                else None
            ),
            generation_config=generation_config or None,
        )
        raw = trace_model_call(
            lambda: client.generate_content(provider_request),
            provider="gemini",
            model_name=self._model_name,
            system_prompt=request.system_prompt,
            messages=messages,
            tools=tools,
            request_payload=provider_request.to_dict(),
            project_name=self._project_name,
            enabled=self._tracing_enabled or None,
        )
        return self._parse_gemini_response(raw)

    def _generate_grok_turn(
        self,
        *,
        request: AgentModelRequest,
        messages: list[ProviderMessageDTO],
        tools: list[ToolDefinition],
    ) -> AgentModelResponse:
        client = self._openai_style_client()
        provider_request = GrokChatCompletionRequestDTO(
            model_name=self._model_name,
            system_prompt=request.system_prompt,
            messages=tuple(messages),
            tools=tuple(tools),
            max_tokens=self._max_output_tokens,
            temperature=self._temperature,
            reasoning_effort=self._reasoning_effort,
        )
        raw = trace_model_call(
            lambda: client.create_chat_completion(provider_request),
            provider="grok",
            model_name=self._model_name,
            system_prompt=request.system_prompt,
            messages=messages,
            tools=tools,
            request_payload=provider_request.to_dict(),
            project_name=self._project_name,
            enabled=self._tracing_enabled or None,
        )
        return self._parse_openai_style_response(raw)

    def _parse_openai_style_response(self, raw: Any) -> AgentModelResponse:
        choice = raw["choices"][0]
        message = choice["message"]
        content = _coerce_message_content(message.get("content"))
        raw_tool_calls = message.get("tool_calls") or []
        tool_calls = [_parse_openai_style_tool_call(item, self._resolve_tool_key) for item in raw_tool_calls]
        if not tool_calls and content.strip():
            salvaged_tool_calls, cleaned_content = self._parse_tool_calls_from_content(content)
            if salvaged_tool_calls:
                tool_calls = salvaged_tool_calls
                content = cleaned_content

        finish_reason = str(choice.get("finish_reason") or "stop")
        return AgentModelResponse(
            assistant_message=content,
            tool_calls=tuple(tool_calls),
            should_continue=bool(tool_calls) or finish_reason == "tool_calls",
        )

    def _parse_anthropic_response(self, raw: Any) -> AgentModelResponse:
        content_blocks = raw.get("content", [])
        assistant_messages: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in content_blocks if isinstance(content_blocks, list) else []:
            if not isinstance(block, Mapping):
                continue
            block_type = block.get("type")
            if block_type == "text":
                text = str(block.get("text", "")).strip()
                if text:
                    assistant_messages.append(text)
            elif block_type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        tool_key=self._resolve_tool_key(str(block.get("name", ""))),
                        arguments=_coerce_mapping(block.get("input")),
                    )
                )
        stop_reason = str(raw.get("stop_reason") or "")
        return AgentModelResponse(
            assistant_message="\n".join(assistant_messages).strip(),
            tool_calls=tuple(tool_calls),
            should_continue=bool(tool_calls) or stop_reason == "tool_use",
        )

    def _parse_gemini_response(self, raw: Any) -> AgentModelResponse:
        candidates = raw.get("candidates") or []
        if not candidates:
            return AgentModelResponse(assistant_message="", should_continue=False)
        candidate = candidates[0]
        content = candidate.get("content") or {}
        parts = content.get("parts") or []
        assistant_messages: list[str] = []
        tool_calls: list[ToolCall] = []
        for part in parts if isinstance(parts, list) else []:
            if not isinstance(part, Mapping):
                continue
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                assistant_messages.append(text.strip())
            function_call = part.get("functionCall") or part.get("function_call")
            if isinstance(function_call, Mapping):
                tool_calls.append(
                    ToolCall(
                        tool_key=self._resolve_tool_key(str(function_call.get("name", ""))),
                        arguments=_coerce_mapping(function_call.get("args")),
                    )
                )
        return AgentModelResponse(
            assistant_message="\n".join(assistant_messages).strip(),
            tool_calls=tuple(tool_calls),
            should_continue=bool(tool_calls),
        )

    def _resolve_tool_key(self, tool_name: str) -> str:
        if tool_name in self._name_to_key:
            return self._name_to_key[tool_name]
        if tool_name in self._name_to_key.values():
            return tool_name
        return f"tool.{tool_name}"

    def _parse_tool_calls_from_content(self, content: str) -> tuple[list[ToolCall], str]:
        text = content.strip()
        if not text.startswith("[TOOL CALL]"):
            return [], content
        blocks = [block.strip() for block in re.split(r"\[TOOL CALL\]\s*", text) if block.strip()]
        tool_calls: list[ToolCall] = []
        for block in blocks:
            tool_name, separator, arguments_text = block.partition("\n")
            if not separator:
                return [], content
            try:
                arguments = json.loads(arguments_text.strip() or "{}")
            except json.JSONDecodeError:
                return [], content
            if not isinstance(arguments, dict):
                return [], content
            tool_calls.append(
                ToolCall(
                    tool_key=self._resolve_tool_key(tool_name.strip()),
                    arguments=arguments,
                )
            )
        return tool_calls, ""


class OpenAIAgentModel(ProviderAgentModel):
    """Provider-backed AgentModel using the OpenAI Chat Completions API."""

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str,
        organization: str | None = None,
        project: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        project_name: str | None = None,
        tracing_enabled: bool = True,
    ) -> None:
        self._api_key = _require_secret(api_key, provider="openai")
        self._organization = _normalize_optional_string(organization)
        self._project = _normalize_optional_string(project)
        super().__init__(
            provider="openai",
            model_name=model_name,
            client=OpenAIClient(
                api_key=self._api_key,
                organization=self._organization,
                project=self._project,
            ),
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            project_name=project_name,
            tracing_enabled=tracing_enabled,
        )

    def with_model_override(self, model_name: str) -> "OpenAIAgentModel":
        return OpenAIAgentModel(
            api_key=self._api_key,
            model_name=model_name,
            organization=self._organization,
            project=self._project,
            temperature=self._temperature,
            max_output_tokens=self._max_output_tokens,
            project_name=self._project_name,
            tracing_enabled=self._tracing_enabled,
        )


class AnthropicAgentModel(ProviderAgentModel):
    """Provider-backed AgentModel using the Anthropic Messages API."""

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        project_name: str | None = None,
        tracing_enabled: bool = True,
    ) -> None:
        self._api_key = _require_secret(api_key, provider="anthropic")
        super().__init__(
            provider="anthropic",
            model_name=model_name,
            client=AnthropicClient(api_key=self._api_key),
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            project_name=project_name,
            tracing_enabled=tracing_enabled,
        )

    def with_model_override(self, model_name: str) -> "AnthropicAgentModel":
        return AnthropicAgentModel(
            api_key=self._api_key,
            model_name=model_name,
            temperature=self._temperature,
            max_output_tokens=self._max_output_tokens,
            project_name=self._project_name,
            tracing_enabled=self._tracing_enabled,
        )


class GeminiAgentModel(ProviderAgentModel):
    """Provider-backed AgentModel using Gemini generateContent."""

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        project_name: str | None = None,
        tracing_enabled: bool = True,
    ) -> None:
        self._api_key = _require_secret(api_key, provider="gemini")
        super().__init__(
            provider="gemini",
            model_name=model_name,
            client=GeminiClient(api_key=self._api_key),
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            project_name=project_name,
            tracing_enabled=tracing_enabled,
        )

    def with_model_override(self, model_name: str) -> "GeminiAgentModel":
        return GeminiAgentModel(
            api_key=self._api_key,
            model_name=model_name,
            temperature=self._temperature,
            max_output_tokens=self._max_output_tokens,
            project_name=self._project_name,
            tracing_enabled=self._tracing_enabled,
        )


class GrokAgentModel(ProviderAgentModel):
    """Provider-backed AgentModel using xAI chat completions."""

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str = DEFAULT_GROK_MODEL,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        reasoning_effort: str | None = None,
        project_name: str | None = None,
        tracing_enabled: bool = True,
    ) -> None:
        self._api_key = _require_secret(api_key, provider="grok")
        super().__init__(
            provider="grok",
            model_name=model_name,
            client=GrokClient(api_key=self._api_key),
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            reasoning_effort=reasoning_effort,
            project_name=project_name,
            tracing_enabled=tracing_enabled,
        )

    def with_model_override(self, model_name: str) -> "GrokAgentModel":
        return GrokAgentModel(
            api_key=self._api_key,
            model_name=model_name,
            temperature=self._temperature,
            max_output_tokens=self._max_output_tokens,
            reasoning_effort=self._reasoning_effort,
            project_name=self._project_name,
            tracing_enabled=self._tracing_enabled,
        )

    def _build_messages(self, request: AgentModelRequest) -> list[ProviderMessageDTO]:
        """Compatibility helper preserved for older tests and callers."""
        return build_provider_messages(request)

    def _parse_response(self, raw: Any) -> AgentModelResponse:
        """Compatibility helper preserved for older tests and callers."""
        return self._parse_openai_style_response(raw)


def parse_model_spec(spec: str) -> tuple[str, str]:
    """Parse `provider:model_name` syntax."""
    provider, separator, model_name = spec.partition(":")
    if not separator:
        raise ValueError(
            f"Model references must use the form provider:model_name. Received '{spec}'."
        )
    normalized_provider = normalize_model_provider(provider)
    normalized_model_name = model_name.strip()
    if not normalized_model_name:
        raise ValueError(f"Model references must include a model name. Received '{spec}'.")
    return normalized_provider, normalized_model_name


def normalize_model_provider(provider: str) -> str:
    normalized_provider = provider.strip().lower()
    if normalized_provider not in _SUPPORTED_PROVIDER_NAMES:
        supported = ", ".join(sorted(_SUPPORTED_PROVIDER_NAMES))
        raise ValueError(
            f"Unsupported model provider '{provider}'. Supported providers: {supported}."
        )
    return normalized_provider


def create_provider_model(
    provider: str,
    *,
    model_name: str,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
    reasoning_effort: str | None = None,
    project_name: str | None = None,
    tracing_enabled: bool | None = None,
) -> ProviderAgentModel:
    """Construct a provider-backed `AgentModel` from environment-backed credentials."""
    normalized_provider = normalize_model_provider(provider)
    effective_tracing_enabled = _resolve_tracing_enabled(tracing_enabled)
    effective_project_name = _resolve_project_name(project_name)
    if normalized_provider == "openai":
        return OpenAIAgentModel(
            api_key=_require_env(("OPENAI_API_KEY",), provider="openai"),
            model_name=model_name,
            organization=os.environ.get("OPENAI_ORGANIZATION"),
            project=os.environ.get("OPENAI_PROJECT"),
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            project_name=effective_project_name,
            tracing_enabled=effective_tracing_enabled,
        )
    if normalized_provider == "anthropic":
        return AnthropicAgentModel(
            api_key=_require_env(("ANTHROPIC_API_KEY",), provider="anthropic"),
            model_name=model_name,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            project_name=effective_project_name,
            tracing_enabled=effective_tracing_enabled,
        )
    if normalized_provider == "gemini":
        return GeminiAgentModel(
            api_key=_require_env(("GEMINI_API_KEY", "GOOGLE_API_KEY"), provider="gemini"),
            model_name=model_name,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            project_name=effective_project_name,
            tracing_enabled=effective_tracing_enabled,
        )
    if normalized_provider == "grok":
        return GrokAgentModel(
            api_key=_require_env(("XAI_API_KEY",), provider="grok"),
            model_name=model_name,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            reasoning_effort=reasoning_effort,
            project_name=effective_project_name,
            tracing_enabled=effective_tracing_enabled,
        )
    raise ValueError(f"Unsupported provider '{provider}'.")


def create_model_from_spec(
    spec: str,
    *,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
    reasoning_effort: str | None = None,
    project_name: str | None = None,
    tracing_enabled: bool | None = None,
) -> ProviderAgentModel:
    """Construct a provider-backed `AgentModel` from `provider:model_name` syntax."""
    provider, model_name = parse_model_spec(spec)
    return create_provider_model(
        provider,
        model_name=model_name,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        reasoning_effort=reasoning_effort,
        project_name=project_name,
        tracing_enabled=tracing_enabled,
    )


def create_model_from_profile(
    profile: ModelProfile,
    *,
    project_name: str | None = None,
    tracing_enabled: bool | None = None,
) -> ProviderAgentModel:
    """Construct a provider-backed `AgentModel` from one persisted profile."""
    return create_provider_model(
        profile.provider,
        model_name=profile.model_name,
        temperature=profile.temperature,
        max_output_tokens=profile.max_output_tokens,
        reasoning_effort=profile.reasoning_effort,
        project_name=project_name,
        tracing_enabled=tracing_enabled,
    )


def build_provider_messages(request: AgentModelRequest) -> list[ProviderMessageDTO]:
    """Reconstruct a provider-agnostic conversational message list from one agent request."""
    messages: list[ProviderMessageDTO] = []
    parameter_block = request.render_parameter_block().strip()
    messages.append(ProviderMessageDTO(role="user", content=parameter_block or "Continue."))
    entries = list(request.transcript)
    index = 0
    while index < len(entries):
        entry = entries[index]
        if entry.entry_type == "assistant":
            assistant_parts: list[str] = []
            if entry.content.strip():
                assistant_parts.append(entry.content.strip())
            index += 1
            while index < len(entries) and entries[index].entry_type == "tool_call":
                assistant_parts.append(f"[TOOL CALL]\n{entries[index].content}")
                index += 1
            messages.append(
                ProviderMessageDTO(
                    role="assistant",
                    content="\n\n".join(assistant_parts) or "(continued)",
                )
            )
            continue
        if entry.entry_type == "user":
            messages.append(ProviderMessageDTO(role="user", content=entry.content or "(user turn)"))
            index += 1
            continue
        if entry.entry_type in {"tool_result", "summary", "context"}:
            user_parts: list[str] = []
            while index < len(entries) and entries[index].entry_type in {"tool_result", "summary", "context"}:
                current = entries[index]
                if current.entry_type == "tool_result":
                    label = "[TOOL RESULT]"
                elif current.entry_type == "summary":
                    label = "[SUMMARY]"
                else:
                    label = f"[CONTEXT: {current.label or 'Context'}]"
                user_parts.append(f"{label}\n{current.content}".rstrip())
                index += 1
            messages.append(ProviderMessageDTO(role="user", content="\n\n".join(user_parts)))
            continue
        index += 1
    if messages and messages[-1].role == "assistant":
        messages.append(ProviderMessageDTO(role="user", content="Continue."))
    return messages


def create_grok_model() -> GrokAgentModel:
    """Compatibility factory for the historical Grok-only adapter entrypoint."""
    return GrokAgentModel(
        api_key=_require_env(("XAI_API_KEY",), provider="grok"),
        model_name=os.environ.get("GROK_MODEL", DEFAULT_GROK_MODEL).strip() or DEFAULT_GROK_MODEL,
        project_name=_resolve_project_name(None),
        tracing_enabled=_resolve_tracing_enabled(None),
    )


def _build_gemini_contents(messages: Sequence[ProviderMessageDTO]) -> list[GeminiContentDTO]:
    role_map = {
        "user": "user",
        "assistant": "model",
        "system": "user",
    }
    contents: list[GeminiContentDTO] = []
    for message in messages:
        contents.append(
            GeminiContentDTO(
                role=role_map[message.role],
                parts=({"text": message.content},),
            )
        )
    return contents


def _parse_openai_style_tool_call(
    raw_call: Any,
    tool_key_resolver,
) -> ToolCall:
    function_payload = raw_call.get("function", {}) if isinstance(raw_call, Mapping) else {}
    raw_name = str(function_payload.get("name", ""))
    raw_arguments = function_payload.get("arguments") or "{}"
    try:
        arguments = json.loads(raw_arguments)
    except json.JSONDecodeError:
        arguments = {}
    if not isinstance(arguments, dict):
        arguments = {}
    return ToolCall(
        tool_key=tool_key_resolver(raw_name),
        arguments=arguments,
    )


def _coerce_message_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, Mapping):
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    text_parts.append(text.strip())
        return "\n".join(text_parts)
    if content is None:
        return ""
    return str(content)


def _coerce_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, Mapping):
        return {str(key): item for key, item in value.items()}
    return {}


def _normalize_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _require_secret(value: str, *, provider: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise RuntimeError(f"{provider} model adapter requires a non-empty API key.")
    return normalized


def _require_env(names: tuple[str, ...], *, provider: str) -> str:
    for env_name in names:
        raw = os.environ.get(env_name)
        if raw is None:
            continue
        normalized = raw.strip()
        if normalized:
            return normalized
    rendered_names = ", ".join(names)
    raise RuntimeError(
        f"{provider} model adapter requires one of the following environment variables: {rendered_names}."
    )


def _resolve_project_name(project_name: str | None) -> str | None:
    explicit = _normalize_optional_string(project_name)
    if explicit is not None:
        return explicit
    for env_name in ("LANGSMITH_PROJECT", "LANGCHAIN_PROJECT"):
        raw = os.environ.get(env_name)
        normalized = _normalize_optional_string(raw)
        if normalized is not None:
            return normalized
    return None


def _resolve_tracing_enabled(tracing_enabled: bool | None) -> bool:
    if tracing_enabled is not None:
        return tracing_enabled
    raw = os.environ.get("LANGSMITH_TRACING") or os.environ.get("LANGCHAIN_TRACING_V2")
    normalized = raw.strip().lower() if isinstance(raw, str) else ""
    return normalized not in {"false", "0", "no", "off"}


__all__ = [
    "AnthropicAgentModel",
    "DEFAULT_ANTHROPIC_MAX_OUTPUT_TOKENS",
    "DEFAULT_GROK_MODEL",
    "GeminiAgentModel",
    "GrokAgentModel",
    "OpenAIAgentModel",
    "ProviderAgentModel",
    "build_provider_messages",
    "create_grok_model",
    "create_model_from_profile",
    "create_model_from_spec",
    "create_provider_model",
    "normalize_model_provider",
    "parse_model_spec",
]
