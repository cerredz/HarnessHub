"""Tests for harnessiq.providers.exa."""

from __future__ import annotations

import unittest

from harnessiq.providers.exa import (
    ExaClient,
    ExaCredentials,
    build_exa_operation_catalog,
    get_exa_operation,
)
from harnessiq.shared.tools import EXA_REQUEST
from harnessiq.tools.exa import create_exa_tools
from harnessiq.tools.registry import ToolRegistry


class ExaCredentialsTests(unittest.TestCase):
    def test_valid_credentials_accepted(self) -> None:
        c = ExaCredentials(api_key="key123")
        self.assertEqual(c.api_key, "key123")

    def test_blank_api_key_raises(self) -> None:
        with self.assertRaises(ValueError):
            ExaCredentials(api_key="")

    def test_blank_api_key_whitespace_raises(self) -> None:
        with self.assertRaises(ValueError):
            ExaCredentials(api_key="   ")

    def test_zero_timeout_raises(self) -> None:
        with self.assertRaises(ValueError):
            ExaCredentials(api_key="key", timeout_seconds=0)

    def test_default_base_url_set(self) -> None:
        c = ExaCredentials(api_key="key")
        self.assertIn("exa.ai", c.base_url)

    def test_as_redacted_dict_excludes_raw_key(self) -> None:
        c = ExaCredentials(api_key="supersecretkey")
        summary = c.as_redacted_dict()
        self.assertNotIn("supersecretkey", str(summary))


class ExaApiTests(unittest.TestCase):
    def test_build_headers_produces_lowercase_x_api_key(self) -> None:
        from harnessiq.providers.exa.api import build_headers
        headers = build_headers("mykey")
        self.assertEqual(headers["x-api-key"], "mykey")
        self.assertNotIn("Authorization", headers)

    def test_build_headers_with_extra_headers(self) -> None:
        from harnessiq.providers.exa.api import build_headers
        headers = build_headers("k", extra_headers={"X-Custom": "val"})
        self.assertEqual(headers["X-Custom"], "val")
        self.assertIn("x-api-key", headers)


class ExaOperationCatalogTests(unittest.TestCase):
    def test_catalog_is_non_empty(self) -> None:
        catalog = build_exa_operation_catalog()
        self.assertGreater(len(catalog), 0)

    def test_catalog_covers_core_categories(self) -> None:
        catalog = build_exa_operation_catalog()
        categories = {op.category for op in catalog}
        self.assertIn("Search", categories)
        self.assertIn("Contents", categories)
        self.assertIn("Find Similar", categories)
        self.assertIn("Answer", categories)

    def test_search_requires_payload(self) -> None:
        op = get_exa_operation("search")
        self.assertTrue(op.payload_required)
        self.assertEqual(op.method, "POST")

    def test_get_contents_requires_payload(self) -> None:
        op = get_exa_operation("get_contents")
        self.assertTrue(op.payload_required)
        self.assertEqual(op.method, "POST")

    def test_get_webset_requires_webset_id(self) -> None:
        op = get_exa_operation("get_webset")
        self.assertIn("webset_id", op.required_path_params)

    def test_list_websets_allows_query(self) -> None:
        op = get_exa_operation("list_websets")
        self.assertTrue(op.allow_query)

    def test_get_operation_raises_for_unknown(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            get_exa_operation("nonexistent_op")
        self.assertIn("nonexistent_op", str(ctx.exception))


class ExaClientTests(unittest.TestCase):
    def _client(self) -> ExaClient:
        creds = ExaCredentials(api_key="testkey")
        return ExaClient(credentials=creds, request_executor=lambda m, u, **kw: {"results": []})

    def test_prepare_request_search_url(self) -> None:
        prepared = self._client().prepare_request("search", payload={"query": "AI trends"})
        self.assertIn("/search", prepared.url)
        self.assertEqual(prepared.method, "POST")

    def test_prepare_request_interpolates_webset_id(self) -> None:
        prepared = self._client().prepare_request("get_webset", path_params={"webset_id": "ws42"})
        self.assertIn("ws42", prepared.url)

    def test_prepare_request_sets_x_api_key_header(self) -> None:
        prepared = self._client().prepare_request("search", payload={"query": "test"})
        self.assertEqual(prepared.headers["x-api-key"], "testkey")

    def test_prepare_request_raises_on_missing_path_param(self) -> None:
        with self.assertRaises(ValueError):
            self._client().prepare_request("get_webset")

    def test_prepare_request_raises_on_missing_required_payload(self) -> None:
        with self.assertRaises(ValueError):
            self._client().prepare_request("search")

    def test_prepare_request_rejects_payload_on_list_op(self) -> None:
        with self.assertRaises(ValueError):
            self._client().prepare_request("list_websets", payload={"bad": "field"})


class ExaToolsTests(unittest.TestCase):
    def test_create_exa_tools_returns_registerable_tuple(self) -> None:
        creds = ExaCredentials(api_key="testkey")
        tools = create_exa_tools(credentials=creds)
        self.assertEqual(len(tools), 1)
        ToolRegistry(tools)

    def test_tool_definition_key_is_exa_request(self) -> None:
        creds = ExaCredentials(api_key="testkey")
        tools = create_exa_tools(credentials=creds)
        self.assertEqual(tools[0].definition.key, EXA_REQUEST)

    def test_tool_handler_executes_search(self) -> None:
        captured: list[dict[str, object]] = []

        def fake(method: str, url: str, **kwargs: object) -> dict[str, object]:
            captured.append({"method": method, "url": url})
            return {"results": []}

        creds = ExaCredentials(api_key="testkey")
        client = ExaClient(credentials=creds, request_executor=fake)
        tools = create_exa_tools(client=client)
        registry = ToolRegistry(tools)
        result = registry.execute(EXA_REQUEST, {"operation": "search", "payload": {"query": "AI"}})
        self.assertEqual(result.output["operation"], "search")
        self.assertEqual(len(captured), 1)

    def test_create_exa_tools_raises_without_credentials_or_client(self) -> None:
        with self.assertRaises(ValueError):
            create_exa_tools()

    def test_allowed_operations_subset(self) -> None:
        creds = ExaCredentials(api_key="testkey")
        tools = create_exa_tools(credentials=creds, allowed_operations=["search", "get_contents"])
        enum_vals = tools[0].definition.input_schema["properties"]["operation"]["enum"]
        self.assertEqual(set(enum_vals), {"search", "get_contents"})


if __name__ == "__main__":
    unittest.main()
