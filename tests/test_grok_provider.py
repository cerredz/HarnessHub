"""Compatibility tests for the Grok provider until its expansion ticket lands."""

from __future__ import annotations

import unittest

from src.providers.grok.helpers import build_request as build_grok_request
from src.tools import ECHO_TEXT, create_builtin_registry


class GrokCompatibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        registry = create_builtin_registry()
        self.tools = registry.definitions([ECHO_TEXT])
        self.messages = [
            {"role": "user", "content": "ping"},
            {"role": "assistant", "content": "pong"},
        ]

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


if __name__ == "__main__":
    unittest.main()
