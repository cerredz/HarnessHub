"""Tests for harnessiq.providers.salesforge."""

from __future__ import annotations

import unittest

from harnessiq.providers.salesforge.operations import (
    SalesforgeOperation,
    build_salesforge_operation_catalog,
    get_salesforge_operation,
)
from harnessiq.shared.dtos import ProviderPayloadRequestDTO, ProviderPayloadResultDTO
from harnessiq.shared.tools import SALESFORGE_REQUEST
from harnessiq.tools.salesforge import create_salesforge_tools
from harnessiq.tools.registry import ToolRegistry


class SalesforgeOperationCatalogTests(unittest.TestCase):
    def test_catalog_is_non_empty(self) -> None:
        catalog = build_salesforge_operation_catalog()
        self.assertGreater(len(catalog), 0)

    def test_catalog_covers_core_categories(self) -> None:
        catalog = build_salesforge_operation_catalog()
        categories = {op.category for op in catalog}
        self.assertIn("Sequence", categories)
        self.assertIn("Sequence Contact", categories)
        self.assertIn("Contact", categories)
        self.assertIn("Mailbox", categories)
        self.assertIn("Unsubscribe", categories)

    def test_list_sequences_is_in_catalog(self) -> None:
        op = get_salesforge_operation("list_sequences")
        self.assertEqual(op.category, "Sequence")

    def test_list_contacts_is_in_catalog(self) -> None:
        op = get_salesforge_operation("list_contacts")
        self.assertEqual(op.category, "Contact")

    def test_get_operation_raises_for_unknown(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            get_salesforge_operation("nonexistent_op")
        self.assertIn("nonexistent_op", str(ctx.exception))


class SalesforgeClientTests(unittest.TestCase):
    def test_execute_operation_accepts_payload_request_dto(self) -> None:
        from harnessiq.providers.salesforge.client import SalesforgeClient

        client = SalesforgeClient(
            api_key="testkey",
            request_executor=lambda m, u, **kw: {"data": []},
        )

        result = client.execute_operation(
            ProviderPayloadRequestDTO(operation="list_sequences", payload={})
        )

        self.assertIsInstance(result, ProviderPayloadResultDTO)
        self.assertEqual(result.operation, "list_sequences")


class SalesforgeToolsTests(unittest.TestCase):
    def _client(self):
        from harnessiq.providers.salesforge.client import SalesforgeClient
        return SalesforgeClient(
            api_key="testkey",
            request_executor=lambda m, u, **kw: [{"id": "s1"}],
        )

    def test_create_salesforge_tools_returns_registerable_tuple(self) -> None:
        tools = create_salesforge_tools(client=self._client())
        self.assertEqual(len(tools), 1)
        ToolRegistry(tools)

    def test_tool_definition_key_is_salesforge_request(self) -> None:
        tools = create_salesforge_tools(client=self._client())
        self.assertEqual(tools[0].definition.key, SALESFORGE_REQUEST)

    def test_tool_handler_executes_list_sequences(self) -> None:
        captured = []

        def fake(method, url, **kw):
            captured.append({"method": method, "url": url})
            return [{"id": "s1"}]

        from harnessiq.providers.salesforge.client import SalesforgeClient
        client = SalesforgeClient(api_key="testkey", request_executor=fake)
        tools = create_salesforge_tools(client=client)
        registry = ToolRegistry(tools)
        result = registry.execute(SALESFORGE_REQUEST, {"operation": "list_sequences"})
        self.assertEqual(result.output["operation"], "list_sequences")
        self.assertGreaterEqual(len(captured), 1)

    def test_create_salesforge_tools_raises_without_credentials_or_client(self) -> None:
        with self.assertRaises(ValueError):
            create_salesforge_tools()

    def test_allowed_operations_subset(self) -> None:
        tools = create_salesforge_tools(
            client=self._client(),
            allowed_operations=["list_sequences", "get_sequence"],
        )
        enum_vals = tools[0].definition.input_schema["properties"]["operation"]["enum"]
        self.assertEqual(set(enum_vals), {"list_sequences", "get_sequence"})


if __name__ == "__main__":
    unittest.main()
