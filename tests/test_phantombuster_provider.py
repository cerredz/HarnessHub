"""Tests for harnessiq.providers.phantombuster."""

from __future__ import annotations

import unittest

from harnessiq.providers.phantombuster.operations import (
    PhantomBusterOperation,
    build_phantombuster_operation_catalog,
    get_phantombuster_operation,
)
from harnessiq.shared.dtos import ProviderPayloadRequestDTO, ProviderPayloadResultDTO
from harnessiq.shared.tools import PHANTOMBUSTER_REQUEST
from harnessiq.tools.phantombuster import create_phantombuster_tools
from harnessiq.tools.registry import ToolRegistry


class PhantomBusterOperationCatalogTests(unittest.TestCase):
    def test_catalog_is_non_empty(self) -> None:
        catalog = build_phantombuster_operation_catalog()
        self.assertGreater(len(catalog), 0)

    def test_catalog_covers_core_categories(self) -> None:
        catalog = build_phantombuster_operation_catalog()
        categories = {op.category for op in catalog}
        self.assertIn("Agent", categories)
        self.assertIn("Container", categories)
        self.assertIn("Phantom", categories)
        self.assertIn("Script", categories)
        self.assertIn("Account", categories)

    def test_list_agents_is_in_catalog(self) -> None:
        op = get_phantombuster_operation("list_agents")
        self.assertEqual(op.category, "Agent")

    def test_get_user_info_is_in_catalog(self) -> None:
        op = get_phantombuster_operation("get_user_info")
        self.assertEqual(op.category, "Account")

    def test_get_operation_raises_for_unknown(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            get_phantombuster_operation("nonexistent_op")
        self.assertIn("nonexistent_op", str(ctx.exception))


class PhantomBusterClientTests(unittest.TestCase):
    def test_execute_operation_accepts_payload_request_dto(self) -> None:
        from harnessiq.providers.phantombuster.client import PhantomBusterClient

        client = PhantomBusterClient(
            api_key="testkey",
            request_executor=lambda m, u, **kw: {"data": []},
        )

        result = client.execute_operation(
            ProviderPayloadRequestDTO(operation="list_agents", payload={})
        )

        self.assertIsInstance(result, ProviderPayloadResultDTO)
        self.assertEqual(result.operation, "list_agents")


class PhantomBusterToolsTests(unittest.TestCase):
    def _client(self):
        from harnessiq.providers.phantombuster.client import PhantomBusterClient
        return PhantomBusterClient(
            api_key="testkey",
            request_executor=lambda m, u, **kw: [{"id": "a1"}],
        )

    def test_create_phantombuster_tools_returns_registerable_tuple(self) -> None:
        tools = create_phantombuster_tools(client=self._client())
        self.assertEqual(len(tools), 1)
        ToolRegistry(tools)

    def test_tool_definition_key_is_phantombuster_request(self) -> None:
        tools = create_phantombuster_tools(client=self._client())
        self.assertEqual(tools[0].definition.key, PHANTOMBUSTER_REQUEST)

    def test_tool_handler_executes_list_agents(self) -> None:
        captured = []

        def fake(method, url, **kw):
            captured.append({"method": method, "url": url})
            return [{"id": "a1"}]

        from harnessiq.providers.phantombuster.client import PhantomBusterClient
        client = PhantomBusterClient(api_key="testkey", request_executor=fake)
        tools = create_phantombuster_tools(client=client)
        registry = ToolRegistry(tools)
        result = registry.execute(PHANTOMBUSTER_REQUEST, {"operation": "list_agents"})
        self.assertEqual(result.output["operation"], "list_agents")
        self.assertGreaterEqual(len(captured), 1)

    def test_create_phantombuster_tools_raises_without_credentials_or_client(self) -> None:
        with self.assertRaises(ValueError):
            create_phantombuster_tools()

    def test_allowed_operations_subset(self) -> None:
        tools = create_phantombuster_tools(
            client=self._client(),
            allowed_operations=["list_agents", "launch_agent"],
        )
        enum_vals = tools[0].definition.input_schema["properties"]["operation"]["enum"]
        self.assertEqual(set(enum_vals), {"list_agents", "launch_agent"})


if __name__ == "__main__":
    unittest.main()
