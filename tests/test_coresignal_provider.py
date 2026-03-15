"""Tests for harnessiq.providers.coresignal."""

from __future__ import annotations

import unittest

from harnessiq.providers.coresignal.operations import (
    CoreSignalOperation,
    build_coresignal_operation_catalog,
    get_coresignal_operation,
)
from harnessiq.shared.tools import CORESIGNAL_REQUEST
from harnessiq.tools.coresignal import create_coresignal_tools
from harnessiq.tools.registry import ToolRegistry


class CoreSignalOperationCatalogTests(unittest.TestCase):
    def test_catalog_is_non_empty(self) -> None:
        catalog = build_coresignal_operation_catalog()
        self.assertGreater(len(catalog), 0)

    def test_catalog_covers_core_categories(self) -> None:
        catalog = build_coresignal_operation_catalog()
        categories = {op.category for op in catalog}
        self.assertIn("Employee", categories)
        self.assertIn("Company", categories)
        self.assertIn("Job", categories)

    def test_search_employees_by_filter_is_in_catalog(self) -> None:
        op = get_coresignal_operation("search_employees_by_filter")
        self.assertEqual(op.category, "Employee")

    def test_get_company_is_in_catalog(self) -> None:
        op = get_coresignal_operation("get_company")
        self.assertEqual(op.category, "Company")

    def test_get_operation_raises_for_unknown(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            get_coresignal_operation("nonexistent_op")
        self.assertIn("nonexistent_op", str(ctx.exception))


class CoreSignalToolsTests(unittest.TestCase):
    def _client(self):
        from harnessiq.providers.coresignal.client import CoreSignalClient
        return CoreSignalClient(
            api_key="testkey",
            request_executor=lambda m, u, **kw: {"data": []},
        )

    def test_create_coresignal_tools_returns_registerable_tuple(self) -> None:
        tools = create_coresignal_tools(client=self._client())
        self.assertEqual(len(tools), 1)
        ToolRegistry(tools)

    def test_tool_definition_key_is_coresignal_request(self) -> None:
        tools = create_coresignal_tools(client=self._client())
        self.assertEqual(tools[0].definition.key, CORESIGNAL_REQUEST)

    def test_tool_handler_executes_search_employees_by_filter(self) -> None:
        captured = []

        def fake(method, url, **kw):
            captured.append({"method": method, "url": url})
            return {"data": []}

        from harnessiq.providers.coresignal.client import CoreSignalClient
        client = CoreSignalClient(api_key="testkey", request_executor=fake)
        tools = create_coresignal_tools(client=client)
        registry = ToolRegistry(tools)
        result = registry.execute(
            CORESIGNAL_REQUEST,
            {"operation": "search_employees_by_filter", "payload": {}},
        )
        self.assertEqual(result.output["operation"], "search_employees_by_filter")
        self.assertGreaterEqual(len(captured), 1)

    def test_create_coresignal_tools_raises_without_credentials_or_client(self) -> None:
        with self.assertRaises(ValueError):
            create_coresignal_tools()

    def test_allowed_operations_subset(self) -> None:
        tools = create_coresignal_tools(
            client=self._client(),
            allowed_operations=["search_employees_by_filter", "get_employee"],
        )
        enum_vals = tools[0].definition.input_schema["properties"]["operation"]["enum"]
        self.assertEqual(set(enum_vals), {"search_employees_by_filter", "get_employee"})


if __name__ == "__main__":
    unittest.main()
