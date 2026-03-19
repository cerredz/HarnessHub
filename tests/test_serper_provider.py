"""Tests for harnessiq.providers.serper."""

from __future__ import annotations

import unittest

from harnessiq.providers.serper import (
    SerperClient,
    SerperCredentials,
    build_serper_operation_catalog,
    get_serper_operation,
)
from harnessiq.shared.tools import SERPER_REQUEST
from harnessiq.tools.registry import ToolRegistry
from harnessiq.tools.serper import create_serper_tools


class SerperCredentialsTests(unittest.TestCase):
    def test_valid_credentials_accepted(self) -> None:
        c = SerperCredentials(api_key="key123")
        self.assertEqual(c.api_key, "key123")

    def test_blank_api_key_raises(self) -> None:
        with self.assertRaises(ValueError):
            SerperCredentials(api_key="")

    def test_blank_api_key_whitespace_raises(self) -> None:
        with self.assertRaises(ValueError):
            SerperCredentials(api_key="   ")

    def test_zero_timeout_raises(self) -> None:
        with self.assertRaises(ValueError):
            SerperCredentials(api_key="key", timeout_seconds=0)

    def test_default_base_url_set(self) -> None:
        c = SerperCredentials(api_key="key")
        self.assertIn("serper.dev", c.base_url)

    def test_as_redacted_dict_excludes_raw_key(self) -> None:
        c = SerperCredentials(api_key="supersecretkey")
        summary = c.as_redacted_dict()
        self.assertNotIn("supersecretkey", str(summary))


class SerperApiTests(unittest.TestCase):
    def test_build_headers_produces_api_key_header(self) -> None:
        from harnessiq.providers.serper.api import build_headers

        headers = build_headers("mykey")
        self.assertEqual(headers["X-API-KEY"], "mykey")

    def test_build_headers_with_extra_headers(self) -> None:
        from harnessiq.providers.serper.api import build_headers

        headers = build_headers("mykey", extra_headers={"X-Custom": "val"})
        self.assertEqual(headers["X-Custom"], "val")
        self.assertIn("X-API-KEY", headers)


class SerperOperationCatalogTests(unittest.TestCase):
    def test_catalog_is_non_empty(self) -> None:
        catalog = build_serper_operation_catalog()
        self.assertGreater(len(catalog), 0)

    def test_catalog_covers_core_categories(self) -> None:
        catalog = build_serper_operation_catalog()
        categories = {op.category for op in catalog}
        self.assertIn("Search", categories)
        self.assertIn("Maps", categories)
        self.assertIn("Research", categories)

    def test_search_requires_payload(self) -> None:
        op = get_serper_operation("search")
        self.assertTrue(op.payload_required)
        self.assertEqual(op.method, "POST")

    def test_scholar_is_in_catalog(self) -> None:
        op = get_serper_operation("scholar")
        self.assertEqual(op.category, "Research")

    def test_get_operation_raises_for_unknown(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            get_serper_operation("nonexistent_op")
        self.assertIn("nonexistent_op", str(ctx.exception))


class SerperClientTests(unittest.TestCase):
    def _client(self) -> SerperClient:
        creds = SerperCredentials(api_key="testkey")
        return SerperClient(credentials=creds, request_executor=lambda m, u, **kw: {"results": []})

    def test_prepare_request_search_url(self) -> None:
        prepared = self._client().prepare_request("search", payload={"q": "AI trends"})
        self.assertIn("/search", prepared.url)
        self.assertEqual(prepared.method, "POST")

    def test_prepare_request_sets_api_key_header(self) -> None:
        prepared = self._client().prepare_request("news", payload={"q": "AI"})
        self.assertEqual(prepared.headers["X-API-KEY"], "testkey")

    def test_prepare_request_rejects_missing_payload(self) -> None:
        with self.assertRaises(ValueError):
            self._client().prepare_request("search")

    def test_prepare_request_rejects_path_params(self) -> None:
        with self.assertRaises(ValueError):
            self._client().prepare_request("search", path_params={"bad": "field"}, payload={"q": "AI"})


class SerperToolsTests(unittest.TestCase):
    def test_create_serper_tools_returns_registerable_tuple(self) -> None:
        creds = SerperCredentials(api_key="testkey")
        tools = create_serper_tools(credentials=creds)
        self.assertEqual(len(tools), 1)
        ToolRegistry(tools)

    def test_tool_definition_key_is_serper_request(self) -> None:
        creds = SerperCredentials(api_key="testkey")
        tools = create_serper_tools(credentials=creds)
        self.assertEqual(tools[0].definition.key, SERPER_REQUEST)

    def test_tool_handler_executes_search(self) -> None:
        captured: list[dict[str, object]] = []

        def fake(method: str, url: str, **kwargs: object) -> dict[str, object]:
            captured.append({"method": method, "url": url})
            return {"organic": []}

        creds = SerperCredentials(api_key="testkey")
        client = SerperClient(credentials=creds, request_executor=fake)
        tools = create_serper_tools(client=client)
        registry = ToolRegistry(tools)
        result = registry.execute(SERPER_REQUEST, {"operation": "search", "payload": {"q": "AI"}})
        self.assertEqual(result.output["operation"], "search")
        self.assertEqual(len(captured), 1)

    def test_create_serper_tools_raises_without_credentials_or_client(self) -> None:
        with self.assertRaises(ValueError):
            create_serper_tools()

    def test_allowed_operations_subset(self) -> None:
        creds = SerperCredentials(api_key="testkey")
        tools = create_serper_tools(credentials=creds, allowed_operations=["search", "news"])
        enum_vals = tools[0].definition.input_schema["properties"]["operation"]["enum"]
        self.assertEqual(set(enum_vals), {"search", "news"})


if __name__ == "__main__":
    unittest.main()
