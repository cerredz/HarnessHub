"""Tests for the OpenAI provider client and request builders."""

from __future__ import annotations

from dataclasses import dataclass
import unittest

from harnessiq.providers.openai import (
    OpenAIClient,
    OpenAIChatCompletionRequestDTO,
    OpenAIEmbeddingRequestDTO,
    OpenAIResponseRequestDTO,
    build_chat_completion_request,
    build_chat_response_format_json_object,
    build_chat_response_format_json_schema,
    build_code_interpreter_tool,
    build_computer_use_tool,
    build_file_search_tool,
    build_image_generation_tool,
    build_json_schema_output,
    build_mcp_tool,
    build_request,
    build_response_input_file,
    build_response_input_image,
    build_response_input_message,
    build_response_input_text,
    build_response_request,
    build_response_text_config,
    build_tool_choice,
    build_web_search_location,
    build_web_search_tool,
    format_tool_definition,
)
from harnessiq.shared.dtos import ProviderMessageDTO
from harnessiq.tools import ECHO_TEXT, create_builtin_registry


class OpenAIProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        registry = create_builtin_registry()
        self.tools = registry.definitions([ECHO_TEXT])
        self.messages = [
            ProviderMessageDTO(role="user", content="ping"),
            ProviderMessageDTO(role="assistant", content="pong"),
        ]

    def test_format_tool_definition_uses_function_shape_and_default_strict_false(self) -> None:
        tool_payload = format_tool_definition(self.tools[0])

        self.assertEqual(tool_payload["type"], "function")
        self.assertEqual(tool_payload["function"]["name"], "echo_text")
        self.assertFalse(tool_payload["function"]["strict"])

    def test_build_request_preserves_existing_chat_completion_behavior(self) -> None:
        request = build_request(
            OpenAIChatCompletionRequestDTO(
                model_name="gpt-4.1",
                system_prompt="Be precise.",
                messages=tuple(self.messages),
                tools=tuple(self.tools),
            )
        )

        self.assertEqual(request["messages"][0], {"role": "system", "content": "Be precise."})
        self.assertEqual(request["tools"][0]["type"], "function")
        self.assertEqual(request["tools"][0]["function"]["name"], "echo_text")

    def test_build_chat_completion_request_supports_tool_choice_and_structured_output(self) -> None:
        response_format = build_chat_response_format_json_schema(
            "echo_response",
            {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
                "additionalProperties": False,
            },
            strict=True,
        )
        request = build_chat_completion_request(
            OpenAIChatCompletionRequestDTO(
                model_name="gpt-4.1",
                system_prompt="Be precise.",
                messages=tuple(self.messages),
                tools=tuple(self.tools),
                tool_choice=build_tool_choice(tool_name="echo_text"),
                response_format=response_format,
                parallel_tool_calls=True,
            )
        )

        self.assertEqual(request["tool_choice"]["function"]["name"], "echo_text")
        self.assertTrue(request["parallel_tool_calls"])
        self.assertEqual(request["response_format"]["json_schema"]["strict"], True)

    def test_build_chat_completion_request_serializes_dto_response_format(self) -> None:
        @dataclass(frozen=True)
        class _FakeDTO:
            payload: dict[str, object]

            def to_dict(self) -> dict[str, object]:
                return dict(self.payload)

        request = build_chat_completion_request(
            OpenAIChatCompletionRequestDTO(
                model_name="gpt-4.1",
                system_prompt="Be precise.",
                messages=tuple(self.messages),
                response_format=_FakeDTO({"type": "json_object"}),
            )
        )

        self.assertEqual(request["response_format"], {"type": "json_object"})

    def test_build_response_request_supports_built_in_tools_and_text_config(self) -> None:
        input_items = [
            build_response_input_message(
                "user",
                [
                    build_response_input_text("Describe the image."),
                    build_response_input_image("https://example.com/cat.png", detail="high"),
                ],
            )
        ]
        web_location = build_web_search_location(city="Indianapolis", country="US", timezone="America/Indiana/Indianapolis")
        request = build_response_request(
            OpenAIResponseRequestDTO(
                model_name="gpt-4.1",
                input_items=tuple(input_items),
                instructions="Use tools when needed.",
                tools=(
                    build_file_search_tool(["vs_123"]),
                    build_web_search_tool(user_location=web_location, search_context_size="high"),
                    build_code_interpreter_tool(container="auto"),
                    build_image_generation_tool(size="1024x1024", quality="high"),
                    build_computer_use_tool(display_width=1280, display_height=720, environment="browser"),
                    build_mcp_tool(server_label="docs", server_url="https://mcp.example.com"),
                ),
                text=build_response_text_config(
                    format=build_json_schema_output(
                        "answer",
                        {
                            "type": "object",
                            "properties": {"summary": {"type": "string"}},
                            "required": ["summary"],
                            "additionalProperties": False,
                        },
                        strict=True,
                    ),
                    verbosity="medium",
                ),
                tool_choice="auto",
                parallel_tool_calls=True,
            ),
        )

        self.assertEqual(request["input"][0]["content"][1]["type"], "input_image")
        self.assertEqual(request["tools"][0]["type"], "file_search")
        self.assertEqual(request["tools"][1]["user_location"]["city"], "Indianapolis")
        self.assertEqual(request["tools"][4]["type"], "computer_use_preview")
        self.assertEqual(request["tools"][5]["type"], "mcp")
        self.assertEqual(request["text"]["format"]["name"], "answer")

    def test_build_response_input_file_supports_file_id_and_inline_data(self) -> None:
        file_by_id = build_response_input_file(file_id="file_123")
        file_inline = build_response_input_file(filename="notes.txt", file_data="SGVsbG8=")

        self.assertEqual(file_by_id, {"type": "input_file", "file_id": "file_123"})
        self.assertEqual(
            file_inline,
            {"type": "input_file", "filename": "notes.txt", "file_data": "SGVsbG8="},
        )

    def test_build_chat_response_format_json_object(self) -> None:
        self.assertEqual(build_chat_response_format_json_object(), {"type": "json_object"})

    def test_openai_client_executes_response_request_with_configured_headers(self) -> None:
        captured: dict[str, object] = {}

        def fake_request_executor(method: str, url: str, **kwargs: object) -> dict[str, object]:
            captured["method"] = method
            captured["url"] = url
            captured["kwargs"] = kwargs
            return {"id": "resp_123"}

        client = OpenAIClient(
            api_key="test-key",
            organization="org_123",
            project="proj_123",
            timeout_seconds=9.5,
            request_executor=fake_request_executor,
        )

        response = client.create_response(
            OpenAIResponseRequestDTO(
                model_name="gpt-4.1",
                input_items="Hello world",
                instructions="Answer briefly.",
            )
        )

        self.assertEqual(response, {"id": "resp_123"})
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["url"], "https://api.openai.com/v1/responses")
        self.assertEqual(captured["kwargs"]["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(captured["kwargs"]["headers"]["OpenAI-Organization"], "org_123")
        self.assertEqual(captured["kwargs"]["headers"]["OpenAI-Project"], "proj_123")
        self.assertEqual(captured["kwargs"]["timeout_seconds"], 9.5)
        self.assertEqual(captured["kwargs"]["json_body"]["instructions"], "Answer briefly.")

    def test_openai_client_supports_models_and_embeddings_endpoints(self) -> None:
        calls: list[tuple[str, str, dict[str, object]]] = []

        def fake_request_executor(method: str, url: str, **kwargs: object) -> dict[str, object]:
            calls.append((method, url, dict(kwargs)))
            return {"ok": True}

        client = OpenAIClient(api_key="test-key", request_executor=fake_request_executor)

        models_response = client.list_models()
        embeddings_response = client.create_embedding(
            OpenAIEmbeddingRequestDTO(
                model_name="text-embedding-3-large",
                input_value=("alpha", "beta"),
                dimensions=256,
            )
        )

        self.assertEqual(models_response, {"ok": True})
        self.assertEqual(embeddings_response, {"ok": True})
        self.assertEqual(calls[0][0], "GET")
        self.assertEqual(calls[0][1], "https://api.openai.com/v1/models")
        self.assertIsNone(calls[0][2]["json_body"])
        self.assertEqual(calls[1][1], "https://api.openai.com/v1/embeddings")
        self.assertEqual(calls[1][2]["json_body"]["dimensions"], 256)

    def test_openai_client_supports_chat_completions(self) -> None:
        captured: dict[str, object] = {}

        def fake_request_executor(method: str, url: str, **kwargs: object) -> dict[str, object]:
            captured["method"] = method
            captured["url"] = url
            captured["kwargs"] = kwargs
            return {"id": "chatcmpl_123"}

        client = OpenAIClient(api_key="test-key", request_executor=fake_request_executor)

        response = client.create_chat_completion(
            OpenAIChatCompletionRequestDTO(
                model_name="gpt-4.1",
                system_prompt="Be precise.",
                messages=tuple(self.messages),
                tools=tuple(self.tools),
                tool_choice=build_tool_choice(tool_name="echo_text"),
            )
        )

        self.assertEqual(response, {"id": "chatcmpl_123"})
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["url"], "https://api.openai.com/v1/chat/completions")
        self.assertEqual(captured["kwargs"]["json_body"]["tool_choice"]["function"]["name"], "echo_text")
        self.assertEqual(captured["kwargs"]["json_body"]["messages"][0]["role"], "system")


if __name__ == "__main__":
    unittest.main()
