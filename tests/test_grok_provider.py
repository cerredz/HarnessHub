"""Tests for the Grok provider client and request builders."""

from __future__ import annotations

import unittest

from harnessiq.providers.grok import (
    GrokClient,
    build_chat_completion_request,
    build_code_execution_tool,
    build_collections_search_tool,
    build_mcp_tool,
    build_request,
    build_response_format_json_object,
    build_response_format_json_schema,
    build_search_parameters,
    build_tool_choice,
    build_web_search_tool,
    build_x_search_tool,
    format_tool_definition,
)
from harnessiq.tools import ECHO_TEXT, create_builtin_registry


class GrokProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        registry = create_builtin_registry()
        self.tools = registry.definitions([ECHO_TEXT])
        self.messages = [
            {"role": "user", "content": "ping"},
            {"role": "assistant", "content": "pong"},
        ]

    def test_format_tool_definition_uses_function_shape_without_strict(self) -> None:
        tool_payload = format_tool_definition(self.tools[0])

        self.assertEqual(tool_payload["type"], "function")
        self.assertEqual(tool_payload["function"]["name"], "echo_text")
        self.assertNotIn("strict", tool_payload["function"])

    def test_build_request_preserves_existing_grok_translation(self) -> None:
        request = build_request(
            model_name="grok-2",
            system_prompt="Be precise.",
            messages=self.messages,
            tools=self.tools,
        )

        self.assertEqual(request["messages"][0]["role"], "system")
        self.assertEqual(request["tools"][0]["function"]["parameters"]["type"], "object")
        self.assertNotIn("strict", request["tools"][0]["function"])

    def test_build_chat_completion_request_supports_search_params_and_structured_output(self) -> None:
        response_format = build_response_format_json_schema(
            "answer",
            {
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": ["summary"],
                "additionalProperties": False,
            },
            strict=True,
        )
        search_parameters = build_search_parameters(
            mode="on",
            max_search_results=5,
            return_citations=True,
            sources=["web", "x"],
        )
        request = build_chat_completion_request(
            model_name="grok-3",
            system_prompt="Be precise.",
            messages=self.messages,
            tools=self.tools,
            tool_choice=build_tool_choice(tool_name="echo_text"),
            response_format=response_format,
            search_parameters=search_parameters,
            reasoning_effort="medium",
        )

        self.assertEqual(request["tool_choice"]["function"]["name"], "echo_text")
        self.assertEqual(request["response_format"]["json_schema"]["name"], "answer")
        self.assertTrue(request["search_parameters"]["return_citations"])
        self.assertEqual(request["reasoning_effort"], "medium")

    def test_built_in_tool_builders_cover_search_collections_and_mcp(self) -> None:
        search_parameters = build_search_parameters(mode="on", sources=["web"])
        web_tool = build_web_search_tool(search_parameters=search_parameters)
        x_tool = build_x_search_tool(search_parameters=search_parameters)
        collections_tool = build_collections_search_tool(collection_ids=["col_123"], file_ids=["file_456"], max_num_results=3)
        code_tool = build_code_execution_tool()
        mcp_tool = build_mcp_tool(server_label="docs", server_url="https://mcp.example.com", allowed_tools=["search"])

        self.assertEqual(web_tool["type"], "web_search")
        self.assertEqual(x_tool["type"], "x_search")
        self.assertEqual(collections_tool["collection_ids"], ["col_123"])
        self.assertEqual(collections_tool["file_ids"], ["file_456"])
        self.assertEqual(code_tool, {"type": "code_execution"})
        self.assertEqual(mcp_tool["allowed_tools"], ["search"])

    def test_build_response_format_json_object(self) -> None:
        self.assertEqual(build_response_format_json_object(), {"type": "json_object"})

    def test_grok_client_executes_chat_completion(self) -> None:
        captured: dict[str, object] = {}

        def fake_request_executor(method: str, url: str, **kwargs: object) -> dict[str, object]:
            captured["method"] = method
            captured["url"] = url
            captured["kwargs"] = kwargs
            return {"id": "chatcmpl_123"}

        client = GrokClient(api_key="test-key", timeout_seconds=8.0, request_executor=fake_request_executor)

        response = client.create_chat_completion(
            model_name="grok-3",
            system_prompt="Be precise.",
            messages=self.messages,
            tools=self.tools,
            tool_choice=build_tool_choice(tool_name="echo_text"),
            search_parameters=build_search_parameters(mode="on", return_citations=True),
            reasoning_effort="medium",
        )

        self.assertEqual(response, {"id": "chatcmpl_123"})
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["url"], "https://api.x.ai/v1/chat/completions")
        self.assertEqual(captured["kwargs"]["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(captured["kwargs"]["timeout_seconds"], 8.0)
        self.assertTrue(captured["kwargs"]["json_body"]["search_parameters"]["return_citations"])
        self.assertEqual(captured["kwargs"]["json_body"]["tool_choice"]["function"]["name"], "echo_text")
        self.assertEqual(captured["kwargs"]["json_body"]["reasoning_effort"], "medium")

    def test_grok_client_lists_models(self) -> None:
        calls: list[tuple[str, str, dict[str, object]]] = []

        def fake_request_executor(method: str, url: str, **kwargs: object) -> dict[str, object]:
            calls.append((method, url, dict(kwargs)))
            return {"data": []}

        client = GrokClient(api_key="test-key", request_executor=fake_request_executor)

        response = client.list_models()

        self.assertEqual(response, {"data": []})
        self.assertEqual(calls[0][0], "GET")
        self.assertEqual(calls[0][1], "https://api.x.ai/v1/models")
        self.assertIsNone(calls[0][2]["json_body"])


if __name__ == "__main__":
    unittest.main()
