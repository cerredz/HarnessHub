"""Tests for harnessiq.providers.leadiq."""

from __future__ import annotations

import unittest

from harnessiq.providers.leadiq.operations import (
    LeadIQOperation,
    build_leadiq_operation_catalog,
    get_leadiq_operation,
)
from harnessiq.shared.tools import LEADIQ_REQUEST
from harnessiq.tools.leadiq import create_leadiq_tools
from harnessiq.tools.registry import ToolRegistry


class LeadIQOperationCatalogTests(unittest.TestCase):
    def test_catalog_is_non_empty(self) -> None:
        catalog = build_leadiq_operation_catalog()
        self.assertGreater(len(catalog), 0)

    def test_catalog_covers_core_categories(self) -> None:
        catalog = build_leadiq_operation_catalog()
        categories = {op.category for op in catalog}
        self.assertIn("Contact", categories)
        self.assertIn("Company", categories)
        self.assertIn("Lead", categories)
        self.assertIn("Tag", categories)

    def test_search_contacts_is_in_catalog(self) -> None:
        op = get_leadiq_operation("search_contacts")
        self.assertEqual(op.category, "Contact")

    def test_get_tags_is_in_catalog(self) -> None:
        op = get_leadiq_operation("get_tags")
        self.assertEqual(op.category, "Tag")

    def test_get_operation_raises_for_unknown(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            get_leadiq_operation("nonexistent_op")
        self.assertIn("nonexistent_op", str(ctx.exception))


class LeadIQToolsTests(unittest.TestCase):
    def _client(self):
        from harnessiq.providers.leadiq.client import LeadIQClient
        return LeadIQClient(
            api_key="testkey",
            request_executor=lambda m, u, **kw: [{"id": "c1"}],
        )

    def test_create_leadiq_tools_returns_registerable_tuple(self) -> None:
        tools = create_leadiq_tools(client=self._client())
        self.assertEqual(len(tools), 1)
        ToolRegistry(tools)

    def test_tool_definition_key_is_leadiq_request(self) -> None:
        tools = create_leadiq_tools(client=self._client())
        self.assertEqual(tools[0].definition.key, LEADIQ_REQUEST)

    def test_tool_handler_executes_search_contacts(self) -> None:
        captured = []

        def fake(method, url, **kw):
            captured.append({"method": method, "url": url})
            return [{"id": "c1"}]

        from harnessiq.providers.leadiq.client import LeadIQClient
        client = LeadIQClient(api_key="testkey", request_executor=fake)
        tools = create_leadiq_tools(client=client)
        registry = ToolRegistry(tools)
        result = registry.execute(LEADIQ_REQUEST, {"operation": "search_contacts", "payload": {"name": "Alice"}})
        self.assertEqual(result.output["operation"], "search_contacts")
        self.assertGreaterEqual(len(captured), 1)

    def test_create_leadiq_tools_raises_without_credentials_or_client(self) -> None:
        with self.assertRaises(ValueError):
            create_leadiq_tools()

    def test_allowed_operations_subset(self) -> None:
        tools = create_leadiq_tools(
            client=self._client(),
            allowed_operations=["search_contacts", "search_companies"],
        )
        enum_vals = tools[0].definition.input_schema["properties"]["operation"]["enum"]
        self.assertEqual(set(enum_vals), {"search_contacts", "search_companies"})


if __name__ == "__main__":
    unittest.main()
