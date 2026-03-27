"""Tests for the Anthropic provider client and request builders."""

from __future__ import annotations

from dataclasses import dataclass
import unittest

from harnessiq.providers.anthropic import (
    AnthropicClient,
    AnthropicCountTokensRequestDTO,
    AnthropicMessageDTO,
    AnthropicMessageRequestDTO,
    build_bash_tool,
    build_computer_tool,
    build_count_tokens_request,
    build_document_block,
    build_image_block,
    build_image_source,
    build_mcp_server,
    build_message,
    build_message_request,
    build_request,
    build_text_block,
    build_text_editor_tool,
    build_thinking_config,
    build_tool_choice,
    build_tool_result_block,
    build_web_search_tool,
    format_tool_definition,
)
from harnessiq.tools import ECHO_TEXT, create_builtin_registry


class AnthropicProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        registry = create_builtin_registry()
        self.tools = registry.definitions([ECHO_TEXT])
        self.messages = [
            AnthropicMessageDTO(role="user", content="ping"),
            AnthropicMessageDTO(role="assistant", content="pong"),
        ]

    def test_format_tool_definition_uses_input_schema(self) -> None:
        tool_payload = format_tool_definition(self.tools[0])

        self.assertEqual(tool_payload["name"], "echo_text")
        self.assertIn("input_schema", tool_payload)

    def test_build_request_preserves_existing_anthropic_translation(self) -> None:
        request = build_request(
            AnthropicCountTokensRequestDTO(
                model_name="claude-sonnet",
                system_prompt="Be precise.",
                messages=tuple(self.messages),
                tools=tuple(self.tools),
            )
        )

        self.assertEqual(request["system"], "Be precise.")
        self.assertEqual(request["messages"], [message.to_dict() for message in self.messages])
        self.assertEqual(request["tools"][0]["name"], "echo_text")
        self.assertIn("input_schema", request["tools"][0])

    def test_build_message_request_supports_blocks_server_tools_and_mcp(self) -> None:
        text_block = build_text_block("Review this file.")
        image_block = build_image_block(build_image_source(media_type="image/png", data="BASE64"))
        document_block = build_document_block(media_type="application/pdf", data="PDFDATA", title="spec")
        tool_result = build_tool_result_block("toolu_123", "done", is_error=False)
        message = build_message("user", [text_block, image_block, document_block, tool_result])
        request = build_message_request(
            AnthropicMessageRequestDTO(
                model_name="claude-3-7-sonnet",
                messages=(message,),
                max_tokens=1024,
                system_prompt="Be precise.",
                tools=(
                    *self.tools,
                    build_web_search_tool(max_uses=2),
                    build_text_editor_tool(),
                    build_bash_tool(),
                    build_computer_tool(display_width_px=1280, display_height_px=720),
                ),
                tool_choice=build_tool_choice(tool_name="echo_text", disable_parallel_tool_use=True),
                thinking=build_thinking_config(2048),
                mcp_servers=(build_mcp_server(name="docs", url="https://mcp.example.com"),),
                temperature=0.2,
            )
        )

        self.assertEqual(request["messages"][0]["content"][1]["type"], "image")
        self.assertEqual(request["messages"][0]["content"][2]["type"], "document")
        self.assertEqual(request["messages"][0]["content"][3]["type"], "tool_result")
        self.assertEqual(request["tools"][1]["type"], "web_search_20250305")
        self.assertEqual(request["tools"][4]["type"], "computer_20250124")
        self.assertEqual(request["tool_choice"]["name"], "echo_text")
        self.assertTrue(request["tool_choice"]["disable_parallel_tool_use"])
        self.assertEqual(request["thinking"]["budget_tokens"], 2048)
        self.assertEqual(request["mcp_servers"][0]["name"], "docs")

    def test_build_message_request_serializes_dto_thinking_config(self) -> None:
        @dataclass(frozen=True)
        class _FakeDTO:
            payload: dict[str, object]

            def to_dict(self) -> dict[str, object]:
                return dict(self.payload)

        request = build_message_request(
            AnthropicMessageRequestDTO(
                model_name="claude-3-7-sonnet",
                messages=(AnthropicMessageDTO(role="user", content="ping"),),
                max_tokens=256,
                thinking=_FakeDTO({"type": "enabled", "budget_tokens": 32}),
            )
        )

        self.assertEqual(request["thinking"], {"type": "enabled", "budget_tokens": 32})

    def test_build_count_tokens_request_supports_tools(self) -> None:
        request = build_count_tokens_request(
            AnthropicCountTokensRequestDTO(
                model_name="claude-3-7-sonnet",
                messages=tuple(self.messages),
                system_prompt="Be precise.",
                tools=tuple(self.tools),
            )
        )

        self.assertEqual(request["model"], "claude-3-7-sonnet")
        self.assertEqual(request["system"], "Be precise.")
        self.assertEqual(request["tools"][0]["name"], "echo_text")

    def test_anthropic_message_dto_rejects_unsupported_roles(self) -> None:
        with self.assertRaises(ValueError):
            AnthropicMessageDTO(role="system", content="invalid")  # type: ignore[arg-type]

    def test_anthropic_client_executes_message_and_count_token_requests(self) -> None:
        calls: list[tuple[str, str, dict[str, object]]] = []

        def fake_request_executor(method: str, url: str, **kwargs: object) -> dict[str, object]:
            calls.append((method, url, dict(kwargs)))
            return {"ok": True}

        client = AnthropicClient(
            api_key="test-key",
            betas=["token-efficient-tools-2025-02-19"],
            timeout_seconds=7.5,
            request_executor=fake_request_executor,
        )

        message_response = client.create_message(
            AnthropicMessageRequestDTO(
                model_name="claude-3-7-sonnet",
                messages=tuple(self.messages),
                max_tokens=512,
                system_prompt="Be precise.",
                tools=tuple(self.tools),
            )
        )
        token_response = client.count_tokens(
            AnthropicCountTokensRequestDTO(
                model_name="claude-3-7-sonnet",
                messages=tuple(self.messages),
                system_prompt="Be precise.",
                tools=tuple(self.tools),
            )
        )

        self.assertEqual(message_response, {"ok": True})
        self.assertEqual(token_response, {"ok": True})
        self.assertEqual(calls[0][0], "POST")
        self.assertEqual(calls[0][1], "https://api.anthropic.com/v1/messages")
        self.assertEqual(calls[0][2]["headers"]["x-api-key"], "test-key")
        self.assertEqual(calls[0][2]["headers"]["anthropic-version"], "2023-06-01")
        self.assertEqual(calls[0][2]["headers"]["anthropic-beta"], "token-efficient-tools-2025-02-19")
        self.assertEqual(calls[0][2]["timeout_seconds"], 7.5)
        self.assertEqual(calls[1][1], "https://api.anthropic.com/v1/messages/count_tokens")


if __name__ == "__main__":
    unittest.main()
