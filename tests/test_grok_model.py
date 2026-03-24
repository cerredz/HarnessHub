from __future__ import annotations

import unittest

from harnessiq.integrations.grok_model import GrokAgentModel


class GrokAgentModelTests(unittest.TestCase):
    def test_parse_response_salvages_pseudo_tool_calls_from_assistant_content(self) -> None:
        model = GrokAgentModel(api_key="test-key")
        model._name_to_key = {"extract_content": "browser.extract_content"}  # type: ignore[attr-defined]

        response = model._parse_response(  # type: ignore[attr-defined]
            {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": '[TOOL CALL]\nbrowser.extract_content\n{"mode":"maps_place_details"}',
                            "role": "assistant",
                        },
                    }
                ]
            }
        )

        self.assertEqual(response.assistant_message, "")
        self.assertTrue(response.should_continue)
        self.assertEqual(len(response.tool_calls), 1)
        self.assertEqual(response.tool_calls[0].tool_key, "browser.extract_content")
        self.assertEqual(response.tool_calls[0].arguments, {"mode": "maps_place_details"})


if __name__ == "__main__":
    unittest.main()
