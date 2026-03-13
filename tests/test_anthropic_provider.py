"""Compatibility tests for the Anthropic provider until its expansion ticket lands."""

from __future__ import annotations

import unittest

from src.providers.anthropic.helpers import build_request as build_anthropic_request
from src.tools import ECHO_TEXT, create_builtin_registry


class AnthropicCompatibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        registry = create_builtin_registry()
        self.tools = registry.definitions([ECHO_TEXT])
        self.messages = [
            {"role": "user", "content": "ping"},
            {"role": "assistant", "content": "pong"},
        ]

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


if __name__ == "__main__":
    unittest.main()
