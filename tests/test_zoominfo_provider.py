"""Tests for harnessiq.providers.zoominfo."""

from __future__ import annotations

import unittest

from harnessiq.providers.zoominfo.operations import (
    ZoomInfoOperation,
    build_zoominfo_operation_catalog,
    get_zoominfo_operation,
)
from harnessiq.shared.tools import ZOOMINFO_REQUEST
from harnessiq.tools.zoominfo import create_zoominfo_tools
from harnessiq.tools.registry import ToolRegistry


class ZoomInfoOperationCatalogTests(unittest.TestCase):
    def test_catalog_is_non_empty(self) -> None:
        catalog = build_zoominfo_operation_catalog()
        self.assertGreater(len(catalog), 0)

    def test_catalog_covers_core_categories(self) -> None:
        catalog = build_zoominfo_operation_catalog()
        categories = {op.category for op in catalog}
        self.assertIn("Contact", categories)
        self.assertIn("Company", categories)
        self.assertIn("Intent", categories)
        self.assertIn("News", categories)
        self.assertIn("Scoop", categories)
        self.assertIn("Enrichment", categories)
        self.assertIn("Bulk", categories)
        self.assertIn("Utility", categories)

    def test_search_contacts_is_in_catalog(self) -> None:
        op = get_zoominfo_operation("search_contacts")
        self.assertEqual(op.category, "Contact")

    def test_get_usage_is_in_catalog(self) -> None:
        op = get_zoominfo_operation("get_usage")
        self.assertEqual(op.category, "Utility")

    def test_get_operation_raises_for_unknown(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            get_zoominfo_operation("nonexistent_op")
        self.assertIn("nonexistent_op", str(ctx.exception))


class ZoomInfoToolsTests(unittest.TestCase):
    def _client(self):
        from harnessiq.providers.zoominfo.client import ZoomInfoClient

        def fake(method, url, **kw):
            if "authenticate" in url:
                return {"jwt": "testjwt"}
            return {"data": []}

        return ZoomInfoClient(
            username="user",
            password="pass",
            request_executor=fake,
        )

    def test_create_zoominfo_tools_returns_registerable_tuple(self) -> None:
        tools = create_zoominfo_tools(client=self._client())
        self.assertEqual(len(tools), 1)
        ToolRegistry(tools)

    def test_tool_definition_key_is_zoominfo_request(self) -> None:
        tools = create_zoominfo_tools(client=self._client())
        self.assertEqual(tools[0].definition.key, ZOOMINFO_REQUEST)

    def test_tool_handler_executes_get_usage(self) -> None:
        captured = []

        def fake(method, url, **kw):
            captured.append({"method": method, "url": url})
            if "authenticate" in url:
                return {"jwt": "testjwt"}
            return {"usage": {}}

        from harnessiq.providers.zoominfo.client import ZoomInfoClient
        client = ZoomInfoClient(username="user", password="pass", request_executor=fake)
        tools = create_zoominfo_tools(client=client)
        registry = ToolRegistry(tools)
        result = registry.execute(ZOOMINFO_REQUEST, {"operation": "get_usage"})
        self.assertEqual(result.output["operation"], "get_usage")
        self.assertGreaterEqual(len(captured), 1)

    def test_create_zoominfo_tools_raises_without_credentials_or_client(self) -> None:
        with self.assertRaises(ValueError):
            create_zoominfo_tools()

    def test_allowed_operations_subset(self) -> None:
        tools = create_zoominfo_tools(
            client=self._client(),
            allowed_operations=["search_contacts", "search_companies"],
        )
        enum_vals = tools[0].definition.input_schema["properties"]["operation"]["enum"]
        self.assertEqual(set(enum_vals), {"search_contacts", "search_companies"})


if __name__ == "__main__":
    unittest.main()
