"""Tests for the Gemini provider client and request builders."""

from __future__ import annotations

import unittest

from src.providers.gemini import (
    GeminiClient,
    build_cached_content_request,
    build_code_execution_tool,
    build_content,
    build_count_tokens_request,
    build_file_data_part,
    build_file_search_tool,
    build_function_calling_config,
    build_function_tool,
    build_generate_content_request,
    build_generation_config,
    build_google_maps_tool,
    build_google_search_tool,
    build_inline_data_part,
    build_request,
    build_system_instruction,
    build_text_part,
    build_tool_config,
    build_url_context_tool,
    format_tool_definition,
)
from src.tools import ECHO_TEXT, create_builtin_registry


class GeminiProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        registry = create_builtin_registry()
        self.tools = registry.definitions([ECHO_TEXT])
        self.messages = [
            {"role": "user", "content": "ping"},
            {"role": "assistant", "content": "pong"},
        ]

    def test_format_tool_definition_uses_function_declaration_shape(self) -> None:
        tool_payload = format_tool_definition(self.tools[0])

        self.assertEqual(tool_payload["name"], "echo_text")
        self.assertEqual(tool_payload["parameters"]["type"], "object")

    def test_build_request_preserves_existing_gemini_translation(self) -> None:
        request = build_request(
            model_name="gemini-2.0-flash",
            system_prompt="Be precise.",
            messages=self.messages,
            tools=self.tools,
        )

        self.assertEqual(request["system_instruction"], {"parts": [{"text": "Be precise."}]})
        self.assertEqual(request["contents"][0]["role"], "user")
        self.assertEqual(request["contents"][1]["role"], "model")
        self.assertEqual(request["tools"][0]["functionDeclarations"][0]["name"], "echo_text")

    def test_generate_content_request_supports_generation_config_tools_and_cache(self) -> None:
        contents = [
            build_content(
                "user",
                [
                    build_text_part("Summarize this document."),
                    build_inline_data_part(mime_type="image/png", data="BASE64"),
                    build_file_data_part(mime_type="application/pdf", file_uri="gs://bucket/spec.pdf"),
                ],
            )
        ]
        system_instruction = build_system_instruction("Be precise.")
        generation_config = build_generation_config(
            temperature=0.2,
            max_output_tokens=512,
            response_mime_type="application/json",
            response_schema={
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": ["summary"],
            },
        )
        tool_config = build_tool_config(
            function_calling_config=build_function_calling_config(
                mode="ANY",
                allowed_function_names=["echo_text"],
            )
        )
        request = build_generate_content_request(
            contents=contents,
            system_instruction=system_instruction,
            tools=[
                *self.tools,
                build_google_search_tool(),
                build_google_maps_tool(),
                build_url_context_tool(),
                build_code_execution_tool(),
                build_file_search_tool(data_store_ids=["store_123"], max_results=3),
            ],
            tool_config=tool_config,
            generation_config=generation_config,
            cached_content="cachedContents/abc123",
        )

        self.assertEqual(request["contents"][0]["parts"][1]["inlineData"]["mimeType"], "image/png")
        self.assertEqual(request["tools"][0]["functionDeclarations"][0]["name"], "echo_text")
        self.assertIn("googleSearch", request["tools"][1])
        self.assertIn("googleMaps", request["tools"][2])
        self.assertIn("urlContext", request["tools"][3])
        self.assertIn("codeExecution", request["tools"][4])
        self.assertEqual(request["tools"][5]["fileSearch"]["dataStoreIds"], ["store_123"])
        self.assertEqual(request["toolConfig"]["functionCallingConfig"]["mode"], "ANY")
        self.assertEqual(request["generationConfig"]["responseMimeType"], "application/json")
        self.assertEqual(request["cachedContent"], "cachedContents/abc123")

    def test_build_count_tokens_and_cache_requests(self) -> None:
        contents = [build_content("user", [build_text_part("hello")])]
        count_request = build_count_tokens_request(
            contents=contents,
            system_instruction=build_system_instruction("Be precise."),
            tools=self.tools,
        )
        cache_request = build_cached_content_request(
            model_name="models/gemini-2.5-flash",
            contents=contents,
            system_instruction=build_system_instruction("Be precise."),
            tools=[build_function_tool(self.tools)],
            ttl="3600s",
            display_name="Docs cache",
        )

        self.assertEqual(count_request["contents"][0]["role"], "user")
        self.assertEqual(count_request["tools"][0]["functionDeclarations"][0]["name"], "echo_text")
        self.assertEqual(cache_request["model"], "models/gemini-2.5-flash")
        self.assertEqual(cache_request["ttl"], "3600s")
        self.assertEqual(cache_request["displayName"], "Docs cache")

    def test_gemini_client_executes_generate_content_cache_and_models(self) -> None:
        calls: list[tuple[str, str, dict[str, object]]] = []

        def fake_request_executor(method: str, url: str, **kwargs: object) -> dict[str, object]:
            calls.append((method, url, dict(kwargs)))
            return {"ok": True}

        client = GeminiClient(api_key="test-key", timeout_seconds=6.0, request_executor=fake_request_executor)
        contents = [build_content("user", [build_text_part("hello")])]

        generate_response = client.generate_content(
            model_name="models/gemini-2.5-flash",
            contents=contents,
            system_instruction=build_system_instruction("Be precise."),
            tools=self.tools,
        )
        count_response = client.count_tokens(
            model_name="gemini-2.5-flash",
            contents=contents,
        )
        cache_response = client.create_cache(
            model_name="models/gemini-2.5-flash",
            contents=contents,
            ttl="3600s",
        )
        models_response = client.list_models()

        self.assertEqual(generate_response, {"ok": True})
        self.assertEqual(count_response, {"ok": True})
        self.assertEqual(cache_response, {"ok": True})
        self.assertEqual(models_response, {"ok": True})
        self.assertIn("/v1beta/models/gemini-2.5-flash:generateContent?key=test-key", calls[0][1])
        self.assertNotIn("/models/models/", calls[0][1])
        self.assertEqual(calls[0][2]["headers"]["Content-Type"], "application/json")
        self.assertEqual(calls[0][2]["timeout_seconds"], 6.0)
        self.assertIn("/v1beta/models/gemini-2.5-flash:countTokens?key=test-key", calls[1][1])
        self.assertIn("/v1beta/cachedContents?key=test-key", calls[2][1])
        self.assertIn("/v1beta/models?key=test-key", calls[3][1])


if __name__ == "__main__":
    unittest.main()
