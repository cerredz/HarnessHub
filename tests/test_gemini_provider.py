"""Compatibility tests for the Gemini provider until its expansion ticket lands."""

from __future__ import annotations

import unittest

from src.providers.gemini.helpers import build_request as build_gemini_request
from src.tools import ECHO_TEXT, create_builtin_registry


class GeminiCompatibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        registry = create_builtin_registry()
        self.tools = registry.definitions([ECHO_TEXT])
        self.messages = [
            {"role": "user", "content": "ping"},
            {"role": "assistant", "content": "pong"},
        ]

    def test_gemini_request_uses_contents_and_function_declarations(self) -> None:
        request = build_gemini_request(
            model_name="gemini-2.0-flash",
            system_prompt="Be precise.",
            messages=self.messages,
            tools=self.tools,
        )

        self.assertEqual(request["system_instruction"], {"parts": [{"text": "Be precise."}]})
        self.assertEqual(request["contents"][0]["role"], "user")
        self.assertEqual(request["contents"][1]["role"], "model")
        self.assertEqual(request["tools"][0]["functionDeclarations"][0]["name"], "echo_text")


if __name__ == "__main__":
    unittest.main()
