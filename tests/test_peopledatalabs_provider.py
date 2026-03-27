"""Tests for harnessiq.providers.peopledatalabs."""

from __future__ import annotations

import unittest

from harnessiq.providers.peopledatalabs.operations import (
    PeopleDataLabsOperation,
    build_peopledatalabs_operation_catalog,
    get_peopledatalabs_operation,
)
from harnessiq.shared.dtos import ProviderPayloadRequestDTO, ProviderPayloadResultDTO
from harnessiq.shared.tools import PEOPLEDATALABS_REQUEST
from harnessiq.tools.peopledatalabs import create_peopledatalabs_tools
from harnessiq.tools.registry import ToolRegistry


class PeopleDataLabsOperationCatalogTests(unittest.TestCase):
    def test_catalog_is_non_empty(self) -> None:
        catalog = build_peopledatalabs_operation_catalog()
        self.assertGreater(len(catalog), 0)

    def test_catalog_covers_core_categories(self) -> None:
        catalog = build_peopledatalabs_operation_catalog()
        categories = {op.category for op in catalog}
        self.assertIn("Person", categories)
        self.assertIn("Company", categories)
        self.assertIn("School", categories)
        self.assertIn("Location", categories)
        self.assertIn("Utility", categories)

    def test_enrich_person_is_in_catalog(self) -> None:
        op = get_peopledatalabs_operation("enrich_person")
        self.assertEqual(op.category, "Person")

    def test_autocomplete_is_in_catalog(self) -> None:
        op = get_peopledatalabs_operation("autocomplete")
        self.assertEqual(op.category, "Utility")

    def test_get_operation_raises_for_unknown(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            get_peopledatalabs_operation("nonexistent_op")
        self.assertIn("nonexistent_op", str(ctx.exception))


class PeopleDataLabsClientTests(unittest.TestCase):
    def test_execute_operation_accepts_payload_request_dto(self) -> None:
        from harnessiq.providers.peopledatalabs.client import PeopleDataLabsClient

        client = PeopleDataLabsClient(
            api_key="testkey",
            request_executor=lambda m, u, **kw: {"status": "ok"},
        )

        result = client.execute_operation(
            ProviderPayloadRequestDTO(operation="clean_location", payload={"location": "New York, NY"})
        )

        self.assertIsInstance(result, ProviderPayloadResultDTO)
        self.assertEqual(result.operation, "clean_location")


class PeopleDataLabsToolsTests(unittest.TestCase):
    def _client(self):
        from harnessiq.providers.peopledatalabs.client import PeopleDataLabsClient
        return PeopleDataLabsClient(
            api_key="testkey",
            request_executor=lambda m, u, **kw: {"data": []},
        )

    def test_create_peopledatalabs_tools_returns_registerable_tuple(self) -> None:
        tools = create_peopledatalabs_tools(client=self._client())
        self.assertEqual(len(tools), 1)
        ToolRegistry(tools)

    def test_tool_definition_key_is_peopledatalabs_request(self) -> None:
        tools = create_peopledatalabs_tools(client=self._client())
        self.assertEqual(tools[0].definition.key, PEOPLEDATALABS_REQUEST)

    def test_tool_handler_executes_autocomplete(self) -> None:
        captured = []

        def fake(method, url, **kw):
            captured.append({"method": method, "url": url})
            return {"data": []}

        from harnessiq.providers.peopledatalabs.client import PeopleDataLabsClient
        client = PeopleDataLabsClient(api_key="testkey", request_executor=fake)
        tools = create_peopledatalabs_tools(client=client)
        registry = ToolRegistry(tools)
        result = registry.execute(
            PEOPLEDATALABS_REQUEST,
            {"operation": "autocomplete", "payload": {"field": "job_title", "text": "eng"}},
        )
        self.assertEqual(result.output["operation"], "autocomplete")
        self.assertGreaterEqual(len(captured), 1)

    def test_create_peopledatalabs_tools_raises_without_credentials_or_client(self) -> None:
        with self.assertRaises(ValueError):
            create_peopledatalabs_tools()

    def test_allowed_operations_subset(self) -> None:
        tools = create_peopledatalabs_tools(
            client=self._client(),
            allowed_operations=["enrich_person", "search_people"],
        )
        enum_vals = tools[0].definition.input_schema["properties"]["operation"]["enum"]
        self.assertEqual(set(enum_vals), {"enrich_person", "search_people"})


if __name__ == "__main__":
    unittest.main()
