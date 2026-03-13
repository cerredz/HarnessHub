"""Tests for provider request translation helpers."""

from __future__ import annotations

import unittest

from src.providers import ProviderFormatError, SUPPORTED_PROVIDERS, normalize_messages
from src.providers.anthropic.helpers import build_request as build_anthropic_request
from src.providers.gemini.helpers import build_request as build_gemini_request
from src.providers.grok.helpers import build_request as build_grok_request
from src.providers.openai.helpers import build_request as build_openai_request
from src.tools import ECHO_TEXT, create_builtin_registry


class ProviderHelperTests(unittest.TestCase):
    def setUp(self) -> None:
        registry = create_builtin_registry()
        self.tools = registry.definitions([ECHO_TEXT])
        self.messages = [
            {"role": "user", "content": "ping"},
            {"role": "assistant", "content": "pong"},
        ]

    def test_supported_providers_are_stable(self) -> None:
        self.assertEqual(SUPPORTED_PROVIDERS, ("anthropic", "openai", "grok", "gemini"))

    def test_normalize_messages_rejects_unknown_roles(self) -> None:
        with self.assertRaises(ProviderFormatError):
            normalize_messages([{"role": "tool", "content": "nope"}])

    def test_normalize_messages_rejects_inline_system_when_disallowed(self) -> None:
        with self.assertRaises(ProviderFormatError):
            normalize_messages([{"role": "system", "content": "dup"}], allow_system=False)

    def test_anthropic_request_uses_system_and_input_schema(self) -> None:
        request = build_anthropic_request(
            model_name="claude-sonnet",
            system_prompt="Be precise.",
            messages=self.messages,
            tools=self.tools,
        )

        self.assertEqual(request["system"], "Be precise.")
        self.assertEqual(request["messages"], self.messages)
        self.assertEqual(request["tools"][0]["name"], "echo_text")
        self.assertIn("input_schema", request["tools"][0])

    def test_openai_request_prepends_system_message_and_function_tools(self) -> None:
        request = build_openai_request(
            model_name="gpt-4.1",
            system_prompt="Be precise.",
            messages=self.messages,
            tools=self.tools,
        )

        self.assertEqual(request["messages"][0], {"role": "system", "content": "Be precise."})
        self.assertEqual(request["tools"][0]["type"], "function")
        self.assertEqual(request["tools"][0]["function"]["name"], "echo_text")
        self.assertFalse(request["tools"][0]["function"]["strict"])

    def test_grok_request_uses_openai_style_translation(self) -> None:
        request = build_grok_request(
            model_name="grok-2",
            system_prompt="Be precise.",
            messages=self.messages,
            tools=self.tools,
        )

        self.assertEqual(request["messages"][0]["role"], "system")
        self.assertEqual(request["tools"][0]["function"]["parameters"]["type"], "object")
        self.assertNotIn("strict", request["tools"][0]["function"])

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
