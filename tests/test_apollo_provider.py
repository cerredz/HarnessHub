"""Tests for harnessiq.providers.apollo."""

from __future__ import annotations

import unittest

from harnessiq.providers.apollo import ApolloClient, ApolloCredentials
from harnessiq.providers.apollo.api import build_headers
from harnessiq.providers.apollo.operations import (
    APOLLO_REQUEST,
    build_apollo_operation_catalog,
    get_apollo_operation,
)
from harnessiq.tools.apollo import create_apollo_tools
from harnessiq.tools.registry import ToolRegistry


class ApolloCredentialsTests(unittest.TestCase):
    def test_valid_credentials_accepted(self) -> None:
        credentials = ApolloCredentials(api_key="apollo-secret")

        self.assertEqual(credentials.api_key, "apollo-secret")
        self.assertIn("apollo.io", credentials.base_url)

    def test_blank_api_key_raises(self) -> None:
        with self.assertRaises(ValueError):
            ApolloCredentials(api_key="")

    def test_zero_timeout_raises(self) -> None:
        with self.assertRaises(ValueError):
            ApolloCredentials(api_key="key", timeout_seconds=0)

    def test_as_redacted_dict_masks_raw_key(self) -> None:
        credentials = ApolloCredentials(api_key="supersecretkey")

        summary = credentials.as_redacted_dict()

        self.assertNotIn("supersecretkey", str(summary))
        self.assertIn("api_key_masked", summary)


class ApolloApiTests(unittest.TestCase):
    def test_build_headers_includes_x_api_key_and_bearer(self) -> None:
        headers = build_headers("mykey")

        self.assertEqual(headers["X-Api-Key"], "mykey")
        self.assertEqual(headers["Authorization"], "Bearer mykey")


class ApolloOperationCatalogTests(unittest.TestCase):
    def test_catalog_is_non_empty(self) -> None:
        catalog = build_apollo_operation_catalog()

        self.assertGreater(len(catalog), 0)

    def test_catalog_covers_core_categories(self) -> None:
        categories = {operation.category for operation in build_apollo_operation_catalog()}

        self.assertIn("Search", categories)
        self.assertIn("Enrichment", categories)
        self.assertIn("Contact", categories)
        self.assertIn("Sequence", categories)
        self.assertIn("Utility", categories)

    def test_search_people_is_post(self) -> None:
        operation = get_apollo_operation("search_people")

        self.assertEqual(operation.method, "POST")

    def test_view_contact_requires_contact_id(self) -> None:
        operation = get_apollo_operation("view_contact")

        self.assertIn("contact_id", operation.required_path_params)

    def test_get_operation_raises_for_unknown(self) -> None:
        with self.assertRaises(ValueError):
            get_apollo_operation("nonexistent_op")


class ApolloClientTests(unittest.TestCase):
    def _client(self) -> ApolloClient:
        credentials = ApolloCredentials(api_key="testkey")
        return ApolloClient(
            credentials=credentials,
            request_executor=lambda method, url, **kwargs: {"ok": True, "url": url, "method": method},
        )

    def test_prepare_request_search_people_url(self) -> None:
        prepared = self._client().prepare_request(
            "search_people",
            payload={"person_titles": ["VP Sales"]},
        )

        self.assertIn("/mixed_people/api_search", prepared.url)
        self.assertEqual(prepared.method, "POST")

    def test_prepare_request_interpolates_contact_id(self) -> None:
        prepared = self._client().prepare_request(
            "view_contact",
            path_params={"contact_id": "contact-1"},
        )

        self.assertIn("/contacts/contact-1", prepared.url)
        self.assertEqual(prepared.method, "GET")

    def test_prepare_request_includes_query_params(self) -> None:
        prepared = self._client().prepare_request(
            "enrich_organization",
            query={"domain": "example.com"},
        )

        self.assertIn("domain=example.com", prepared.url)

    def test_prepare_request_rejects_missing_path_param(self) -> None:
        with self.assertRaises(ValueError):
            self._client().prepare_request("view_contact")

    def test_prepare_request_rejects_missing_payload(self) -> None:
        with self.assertRaises(ValueError):
            self._client().prepare_request("search_people")

    def test_prepare_request_rejects_payload_for_get(self) -> None:
        with self.assertRaises(ValueError):
            self._client().prepare_request("view_contact", path_params={"contact_id": "contact-1"}, payload={"bad": True})


class ApolloToolsTests(unittest.TestCase):
    def test_create_apollo_tools_returns_registerable_tuple(self) -> None:
        credentials = ApolloCredentials(api_key="testkey")

        tools = create_apollo_tools(credentials=credentials)

        self.assertEqual(len(tools), 1)
        ToolRegistry(tools)

    def test_tool_definition_key_is_apollo_request(self) -> None:
        credentials = ApolloCredentials(api_key="testkey")

        tools = create_apollo_tools(credentials=credentials)

        self.assertEqual(tools[0].definition.key, APOLLO_REQUEST)

    def test_tool_handler_executes_search_people(self) -> None:
        captured: list[dict[str, object]] = []

        def fake(method: str, url: str, **kwargs: object) -> dict[str, object]:
            captured.append({"method": method, "url": url, "json_body": kwargs.get("json_body")})
            return {"people": []}

        client = ApolloClient(
            credentials=ApolloCredentials(api_key="testkey"),
            request_executor=fake,
        )
        registry = ToolRegistry(create_apollo_tools(client=client))

        result = registry.execute(
            APOLLO_REQUEST,
            {"operation": "search_people", "payload": {"person_titles": ["VP Sales"]}},
        )

        self.assertEqual(result.output["operation"], "search_people")
        self.assertEqual(len(captured), 1)
        self.assertIn("/mixed_people/api_search", str(captured[0]["url"]))

    def test_create_apollo_tools_raises_without_credentials_or_client(self) -> None:
        with self.assertRaises(ValueError):
            create_apollo_tools()

    def test_allowed_operations_subset(self) -> None:
        credentials = ApolloCredentials(api_key="testkey")

        tools = create_apollo_tools(
            credentials=credentials,
            allowed_operations=["search_people", "view_usage_stats"],
        )

        enum_values = tools[0].definition.input_schema["properties"]["operation"]["enum"]
        self.assertEqual(set(enum_values), {"search_people", "view_usage_stats"})


if __name__ == "__main__":
    unittest.main()
