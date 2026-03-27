"""Tests for harnessiq.providers.proxycurl."""

from __future__ import annotations

import unittest

from harnessiq.providers.proxycurl.operations import (
    ProxycurlOperation,
    build_proxycurl_operation_catalog,
    get_proxycurl_operation,
)
from harnessiq.shared.dtos import ProviderPayloadRequestDTO, ProviderPayloadResultDTO
from harnessiq.shared.tools import PROXYCURL_REQUEST
from harnessiq.tools.proxycurl import create_proxycurl_tools
from harnessiq.tools.registry import ToolRegistry


class ProxycurlOperationCatalogTests(unittest.TestCase):
    def test_catalog_is_non_empty(self) -> None:
        catalog = build_proxycurl_operation_catalog()
        self.assertGreater(len(catalog), 0)

    def test_catalog_covers_core_categories(self) -> None:
        catalog = build_proxycurl_operation_catalog()
        categories = {op.category for op in catalog}
        self.assertIn("Person", categories)
        self.assertIn("Company", categories)
        self.assertIn("Job", categories)
        self.assertIn("Email", categories)

    def test_scrape_person_profile_is_in_catalog(self) -> None:
        op = get_proxycurl_operation("scrape_person_profile")
        self.assertEqual(op.category, "Person")

    def test_search_jobs_is_in_catalog(self) -> None:
        op = get_proxycurl_operation("search_jobs")
        self.assertEqual(op.category, "Job")

    def test_get_operation_raises_for_unknown(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            get_proxycurl_operation("nonexistent_op")
        self.assertIn("nonexistent_op", str(ctx.exception))


class ProxycurlClientTests(unittest.TestCase):
    def test_execute_operation_accepts_payload_request_dto(self) -> None:
        from harnessiq.providers.proxycurl.client import ProxycurlClient

        client = ProxycurlClient(
            api_key="testkey",
            request_executor=lambda m, u, **kw: {"results": []},
        )

        result = client.execute_operation(
            ProviderPayloadRequestDTO(operation="search_jobs", payload={})
        )

        self.assertIsInstance(result, ProviderPayloadResultDTO)
        self.assertEqual(result.operation, "search_jobs")


class ProxycurlToolsTests(unittest.TestCase):
    def _client(self):
        from harnessiq.providers.proxycurl.client import ProxycurlClient
        return ProxycurlClient(
            api_key="testkey",
            request_executor=lambda m, u, **kw: [],
        )

    def test_create_proxycurl_tools_returns_registerable_tuple(self) -> None:
        tools = create_proxycurl_tools(client=self._client())
        self.assertEqual(len(tools), 1)
        ToolRegistry(tools)

    def test_tool_definition_key_is_proxycurl_request(self) -> None:
        tools = create_proxycurl_tools(client=self._client())
        self.assertEqual(tools[0].definition.key, PROXYCURL_REQUEST)

    def test_tool_handler_executes_search_jobs(self) -> None:
        captured = []

        def fake(method, url, **kw):
            captured.append({"method": method, "url": url})
            return []

        from harnessiq.providers.proxycurl.client import ProxycurlClient
        client = ProxycurlClient(api_key="testkey", request_executor=fake)
        tools = create_proxycurl_tools(client=client)
        registry = ToolRegistry(tools)
        result = registry.execute(PROXYCURL_REQUEST, {"operation": "search_jobs"})
        self.assertEqual(result.output["operation"], "search_jobs")
        self.assertGreaterEqual(len(captured), 1)

    def test_create_proxycurl_tools_raises_without_credentials_or_client(self) -> None:
        with self.assertRaises(ValueError):
            create_proxycurl_tools()

    def test_allowed_operations_subset(self) -> None:
        tools = create_proxycurl_tools(
            client=self._client(),
            allowed_operations=["scrape_person_profile", "scrape_company_profile"],
        )
        enum_vals = tools[0].definition.input_schema["properties"]["operation"]["enum"]
        self.assertEqual(set(enum_vals), {"scrape_person_profile", "scrape_company_profile"})


if __name__ == "__main__":
    unittest.main()
