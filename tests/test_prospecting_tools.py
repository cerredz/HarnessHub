"""Tests for the public browser and prospecting shared tool factories."""

from __future__ import annotations

import unittest

from harnessiq.shared.tools import (
    BROWSER_EXTRACT_CONTENT,
    BROWSER_NAVIGATE,
    EVALUATE_COMPANY,
    SEARCH_OR_SUMMARIZE,
    RegisteredTool,
)
from harnessiq.tools.browser import build_browser_tool_definitions, create_browser_tools
from harnessiq.tools.eval import (
    build_evaluate_company_tool_definition,
    create_evaluate_company_tool,
)
from harnessiq.tools.search import (
    build_search_or_summarize_tool_definition,
    create_search_or_summarize_tool,
)


class ProspectingToolFactoryTests(unittest.TestCase):
    def test_browser_tool_definitions_include_maps_extraction_surface(self) -> None:
        definitions = build_browser_tool_definitions()
        keys = [definition.key for definition in definitions]

        self.assertIn(BROWSER_NAVIGATE, keys)
        self.assertIn(BROWSER_EXTRACT_CONTENT, keys)
        self.assertEqual(definitions[-1].key, BROWSER_EXTRACT_CONTENT)

    def test_create_browser_tools_binds_handlers_by_name(self) -> None:
        handlers = {
            definition.name: (
                lambda arguments, key=definition.key: {"tool_key": key, "arguments": arguments}
            )
            for definition in build_browser_tool_definitions()
        }

        tools = create_browser_tools(handlers=handlers)
        registry = {tool.key: tool for tool in tools}

        self.assertEqual(len(tools), len(build_browser_tool_definitions()))
        self.assertEqual(
            registry[BROWSER_NAVIGATE].execute({"url": "https://example.com"}).output["tool_key"],
            BROWSER_NAVIGATE,
        )

    def test_create_browser_tools_requires_all_handlers(self) -> None:
        with self.assertRaises(KeyError):
            create_browser_tools(handlers={"navigate": lambda arguments: {"ok": True}})

    def test_evaluate_company_tool_uses_shared_key_and_schema(self) -> None:
        tool = create_evaluate_company_tool(
            handler=lambda arguments: {"verdict": "QUALIFIED", "echo": arguments["listing_data"]["name"]}
        )

        self.assertIsInstance(tool, RegisteredTool)
        self.assertEqual(tool.key, EVALUATE_COMPANY)
        result = tool.execute(
            {
                "company_description": "Dentists in New Jersey",
                "eval_system_prompt": "Return JSON.",
                "listing_data": {"name": "Edison Family Dental"},
            }
        )
        self.assertEqual(result.output["verdict"], "QUALIFIED")
        self.assertEqual(result.output["echo"], "Edison Family Dental")

    def test_search_or_summarize_tool_uses_shared_key_and_schema(self) -> None:
        tool = create_search_or_summarize_tool(
            handler=lambda arguments: {
                "action": "continued",
                "next_query": "dentist",
                "next_location": "Edison NJ",
                "next_search_index": arguments["last_completed_search_index"] + 1,
            }
        )

        self.assertEqual(tool.key, SEARCH_OR_SUMMARIZE)
        result = tool.execute(
            {
                "company_description": "Dentists in New Jersey",
                "searches_completed": [],
                "search_history_summary": None,
                "searches_summarized_through": 0,
                "summarize_at_x": 10,
                "last_completed_search_index": -1,
            }
        )
        self.assertEqual(result.output["next_search_index"], 0)

    def test_public_definitions_are_importable(self) -> None:
        evaluate_definition = build_evaluate_company_tool_definition()
        search_definition = build_search_or_summarize_tool_definition()

        self.assertEqual(evaluate_definition.key, EVALUATE_COMPANY)
        self.assertEqual(search_definition.key, SEARCH_OR_SUMMARIZE)


if __name__ == "__main__":
    unittest.main()
