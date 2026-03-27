from __future__ import annotations

from unittest.mock import patch
from typing import Any

from harnessiq.config import ModelProfile
from harnessiq.integrations import (
    AnthropicAgentModel,
    GeminiAgentModel,
    GrokAgentModel,
    OpenAIAgentModel,
    ProviderAgentModel,
    build_provider_messages,
    create_model_from_profile,
    create_model_from_spec,
    parse_model_spec,
)
from harnessiq.shared.agents import AgentModelRequest, AgentTranscriptEntry, json_parameter_section
from harnessiq.shared.tools import ToolDefinition


class _FakeOpenAIStyleClient:
    def __init__(self, *, assistant_message: str = "Completed.") -> None:
        self.assistant_message = assistant_message
        self.calls: list[dict[str, Any]] = []

    def create_chat_completion(
        self,
        *,
        model_name: str,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools=None,
        max_tokens=None,
        temperature=None,
        parallel_tool_calls=None,
        reasoning_effort=None,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "model_name": model_name,
                "system_prompt": system_prompt,
                "messages": messages,
                "tools": tools,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "parallel_tool_calls": parallel_tool_calls,
                "reasoning_effort": reasoning_effort,
            }
        )
        return {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": self.assistant_message,
                        "role": "assistant",
                    },
                }
            ]
        }


class _FakeAnthropicClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def create_message(
        self,
        *,
        model_name: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        system_prompt: str | None = None,
        tools=None,
        tool_choice=None,
        temperature=None,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "model_name": model_name,
                "messages": messages,
                "max_tokens": max_tokens,
                "system_prompt": system_prompt,
                "tools": tools,
                "tool_choice": tool_choice,
                "temperature": temperature,
            }
        )
        return {
            "content": [
                {"type": "text", "text": "Anthropic response."},
                {"type": "tool_use", "name": "browser_extract", "input": {"url": "https://example.com"}},
            ],
            "stop_reason": "tool_use",
        }


class _FakeGeminiClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def generate_content(
        self,
        *,
        model_name: str,
        contents: list[dict[str, Any]],
        system_instruction: dict[str, Any] | None = None,
        tools=None,
        tool_config=None,
        generation_config=None,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "model_name": model_name,
                "contents": contents,
                "system_instruction": system_instruction,
                "tools": tools,
                "tool_config": tool_config,
                "generation_config": generation_config,
            }
        )
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "Gemini response."},
                            {"functionCall": {"name": "browser_extract", "args": {"url": "https://example.com"}}},
                        ]
                    }
                }
            ]
        }


def _build_request() -> AgentModelRequest:
    return AgentModelRequest(
        agent_name="demo_agent",
        system_prompt="You are a precise demo agent.",
        parameter_sections=(json_parameter_section("Goal", {"task": "demo"}),),
        transcript=(
            AgentTranscriptEntry(entry_type="assistant", content="I will inspect the page."),
            AgentTranscriptEntry(
                entry_type="tool_call",
                content='browser.extract\n{"url":"https://example.com"}',
                tool_key="browser.extract",
                arguments={"url": "https://example.com"},
            ),
            AgentTranscriptEntry(
                entry_type="tool_result",
                content='browser.extract\n{"title":"Example Domain"}',
                tool_key="browser.extract",
                output={"title": "Example Domain"},
            ),
        ),
        tools=(
            ToolDefinition(
                key="browser.extract",
                name="browser_extract",
                description="Extract a page.",
                input_schema={
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                    "required": ["url"],
                    "additionalProperties": False,
                },
            ),
        ),
    )


def test_parse_model_spec_normalizes_provider() -> None:
    provider, model_name = parse_model_spec(" OpenAI : gpt-5.4 ")
    assert provider == "openai"
    assert model_name == "gpt-5.4"


def test_build_provider_messages_serializes_transcript() -> None:
    messages = build_provider_messages(_build_request())
    assert messages[0]["role"] == "user"
    assert "## Goal" in messages[0]["content"]
    assert messages[1]["role"] == "assistant"
    assert "I will inspect the page." in messages[1]["content"]
    assert '[TOOL CALL]\nbrowser.extract\n{"url":"https://example.com"}' in messages[1]["content"]
    assert messages[1]["content"].startswith("I will inspect the page.")
    assert messages[2]["role"] == "user"
    assert '[TOOL RESULT]\nbrowser.extract\n{"title":"Example Domain"}' in messages[2]["content"]


def test_anthropic_agent_model_parses_text_and_tool_use_blocks() -> None:
    model = AnthropicAgentModel(api_key="test-key", model_name="claude-3-7-sonnet")
    model._name_to_key = {"browser_extract": "browser.extract"}  # type: ignore[attr-defined]

    response = model._parse_anthropic_response(  # type: ignore[attr-defined]
        {
            "content": [
                {"type": "text", "text": "I found a relevant page."},
                {"type": "tool_use", "name": "browser_extract", "input": {"url": "https://example.com"}},
            ],
            "stop_reason": "tool_use",
        }
    )

    assert response.assistant_message == "I found a relevant page."
    assert response.should_continue is True
    assert response.tool_calls[0].tool_key == "browser.extract"
    assert response.tool_calls[0].arguments == {"url": "https://example.com"}


def test_provider_agent_model_accepts_openai_style_contract_client() -> None:
    client = _FakeOpenAIStyleClient(assistant_message="OpenAI response.")
    model = ProviderAgentModel(provider="openai", model_name="gpt-5.4", client=client, tracing_enabled=False)

    response = model.generate_turn(_build_request())

    assert response.assistant_message == "OpenAI response."
    assert response.should_continue is False
    assert client.calls[0]["model_name"] == "gpt-5.4"
    assert client.calls[0]["parallel_tool_calls"] is True


def test_provider_agent_model_accepts_anthropic_contract_client() -> None:
    client = _FakeAnthropicClient()
    model = ProviderAgentModel(provider="anthropic", model_name="claude-3-7-sonnet", client=client, tracing_enabled=False)

    response = model.generate_turn(_build_request())

    assert response.assistant_message == "Anthropic response."
    assert response.should_continue is True
    assert response.tool_calls[0].tool_key == "browser.extract"
    assert client.calls[0]["max_tokens"] == 4096


def test_provider_agent_model_accepts_gemini_contract_client() -> None:
    client = _FakeGeminiClient()
    model = ProviderAgentModel(provider="gemini", model_name="gemini-2.5-pro", client=client, tracing_enabled=False)

    response = model.generate_turn(_build_request())

    assert response.assistant_message == "Gemini response."
    assert response.should_continue is True
    assert response.tool_calls[0].tool_key == "browser.extract"
    assert client.calls[0]["model_name"] == "gemini-2.5-pro"


def test_provider_agent_model_accepts_grok_openai_style_contract_client() -> None:
    client = _FakeOpenAIStyleClient(assistant_message="Grok response.")
    model = ProviderAgentModel(
        provider="grok",
        model_name="grok-4-1-fast-reasoning",
        client=client,
        reasoning_effort="high",
        tracing_enabled=False,
    )

    response = model.generate_turn(_build_request())

    assert response.assistant_message == "Grok response."
    assert response.should_continue is False
    assert client.calls[0]["reasoning_effort"] == "high"


def test_gemini_agent_model_parses_text_and_function_calls() -> None:
    model = GeminiAgentModel(api_key="test-key", model_name="gemini-2.5-pro")
    model._name_to_key = {"browser_extract": "browser.extract"}  # type: ignore[attr-defined]

    response = model._parse_gemini_response(  # type: ignore[attr-defined]
        {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "Found the page."},
                            {"functionCall": {"name": "browser_extract", "args": {"url": "https://example.com"}}},
                        ]
                    }
                }
            ]
        }
    )

    assert response.assistant_message == "Found the page."
    assert response.should_continue is True
    assert response.tool_calls[0].tool_key == "browser.extract"
    assert response.tool_calls[0].arguments == {"url": "https://example.com"}


def test_create_model_from_spec_reads_provider_env() -> None:
    with patch.dict("os.environ", {"OPENAI_API_KEY": "openai-test-key"}):
        model = create_model_from_spec("openai:gpt-5.4", tracing_enabled=False)
    assert isinstance(model, OpenAIAgentModel)
    assert model.provider == "openai"
    assert model.model_name == "gpt-5.4"


def test_create_model_from_profile_uses_profile_settings() -> None:
    profile = ModelProfile(
        name="work",
        provider="grok",
        model_name="grok-4-1-fast-reasoning",
        reasoning_effort="high",
        max_output_tokens=4096,
    )
    with patch.dict("os.environ", {"XAI_API_KEY": "xai-test-key"}):
        model = create_model_from_profile(profile, tracing_enabled=False)
    assert isinstance(model, GrokAgentModel)
    assert model.provider == "grok"
    assert model.model_name == "grok-4-1-fast-reasoning"
    assert model._max_output_tokens == 4096  # type: ignore[attr-defined]
    assert model._reasoning_effort == "high"  # type: ignore[attr-defined]


def test_grok_agent_model_salvages_pseudo_tool_calls_from_content() -> None:
    model = GrokAgentModel(api_key="test-key")
    model._name_to_key = {"browser.extract": "browser.extract"}  # type: ignore[attr-defined]

    response = model._parse_response(  # type: ignore[attr-defined]
        {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": '[TOOL CALL]\nbrowser.extract\n{"mode":"maps_place_details"}',
                        "role": "assistant",
                    },
                }
            ]
        }
    )

    assert response.assistant_message == ""
    assert response.should_continue is True
    assert response.tool_calls[0].tool_key == "browser.extract"
    assert response.tool_calls[0].arguments == {"mode": "maps_place_details"}
