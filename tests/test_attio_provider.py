"""Tests for harnessiq.providers.attio."""

from __future__ import annotations

import unittest

from harnessiq.providers.attio import (
    AttioClient,
    AttioCredentials,
    build_attio_operation_catalog,
    get_attio_operation,
)
from harnessiq.shared.tools import ATTIO_REQUEST
from harnessiq.tools.attio import create_attio_tools
from harnessiq.tools.registry import ToolRegistry


class AttioCredentialsTests(unittest.TestCase):
    def test_valid_credentials_accepted(self) -> None:
        c = AttioCredentials(api_key="key123")
        self.assertEqual(c.api_key, "key123")

    def test_blank_api_key_raises(self) -> None:
        with self.assertRaises(ValueError):
            AttioCredentials(api_key="")

    def test_blank_api_key_whitespace_raises(self) -> None:
        with self.assertRaises(ValueError):
            AttioCredentials(api_key="   ")

    def test_zero_timeout_raises(self) -> None:
        with self.assertRaises(ValueError):
            AttioCredentials(api_key="key", timeout_seconds=0)

    def test_default_base_url_set(self) -> None:
        c = AttioCredentials(api_key="key")
        self.assertIn("attio.com", c.base_url)

    def test_as_redacted_dict_excludes_raw_key(self) -> None:
        c = AttioCredentials(api_key="supersecretkey")
        summary = c.as_redacted_dict()
        self.assertNotIn("supersecretkey", str(summary))


class AttioApiTests(unittest.TestCase):
    def test_build_headers_produces_bearer_token(self) -> None:
        from harnessiq.providers.attio.api import build_headers

        headers = build_headers("mykey")
        self.assertEqual(headers["Authorization"], "Bearer mykey")

    def test_build_headers_with_extra_headers(self) -> None:
        from harnessiq.providers.attio.api import build_headers

        headers = build_headers("mykey", extra_headers={"X-Custom": "val"})
        self.assertEqual(headers["X-Custom"], "val")
        self.assertIn("Authorization", headers)


class AttioOperationCatalogTests(unittest.TestCase):
    def test_catalog_is_non_empty(self) -> None:
        catalog = build_attio_operation_catalog()
        self.assertGreater(len(catalog), 0)

    def test_catalog_covers_core_categories(self) -> None:
        catalog = build_attio_operation_catalog()
        categories = {op.category for op in catalog}
        self.assertIn("Object", categories)
        self.assertIn("Attribute", categories)
        self.assertIn("Record", categories)

    def test_create_record_requires_payload(self) -> None:
        op = get_attio_operation("create_record")
        self.assertTrue(op.payload_required)
        self.assertEqual(op.method, "POST")

    def test_get_record_requires_path_params(self) -> None:
        op = get_attio_operation("get_record")
        self.assertIn("object", op.required_path_params)
        self.assertIn("record_id", op.required_path_params)

    def test_get_operation_raises_for_unknown(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            get_attio_operation("nonexistent_op")
        self.assertIn("nonexistent_op", str(ctx.exception))


class AttioClientTests(unittest.TestCase):
    def _client(self) -> AttioClient:
        creds = AttioCredentials(api_key="testkey")
        return AttioClient(credentials=creds, request_executor=lambda m, u, **kw: {"results": []})

    def test_prepare_request_list_objects_url(self) -> None:
        prepared = self._client().prepare_request("list_objects")
        self.assertIn("/objects", prepared.url)
        self.assertEqual(prepared.method, "GET")

    def test_prepare_request_interpolates_record_id(self) -> None:
        prepared = self._client().prepare_request(
            "get_record",
            path_params={"object": "people", "record_id": "rec_1"},
        )
        self.assertIn("people", prepared.url)
        self.assertIn("rec_1", prepared.url)

    def test_prepare_request_sets_bearer_header(self) -> None:
        prepared = self._client().prepare_request("list_objects")
        self.assertEqual(prepared.headers["Authorization"], "Bearer testkey")

    def test_prepare_request_raises_on_missing_path_param(self) -> None:
        with self.assertRaises(ValueError):
            self._client().prepare_request("get_record", path_params={"object": "people"})

    def test_prepare_request_raises_on_missing_required_payload(self) -> None:
        with self.assertRaises(ValueError):
            self._client().prepare_request("create_record", path_params={"object": "people"})

    def test_prepare_request_rejects_payload_on_no_payload_op(self) -> None:
        with self.assertRaises(ValueError):
            self._client().prepare_request("list_objects", payload={"bad": "field"})


class AttioToolsTests(unittest.TestCase):
    def test_create_attio_tools_returns_registerable_tuple(self) -> None:
        creds = AttioCredentials(api_key="testkey")
        tools = create_attio_tools(credentials=creds)
        self.assertEqual(len(tools), 1)
        ToolRegistry(tools)

    def test_tool_definition_key_is_attio_request(self) -> None:
        creds = AttioCredentials(api_key="testkey")
        tools = create_attio_tools(credentials=creds)
        self.assertEqual(tools[0].definition.key, ATTIO_REQUEST)

    def test_tool_handler_executes_list_objects(self) -> None:
        captured: list[dict[str, object]] = []

        def fake(method: str, url: str, **kwargs: object) -> dict[str, object]:
            captured.append({"method": method, "url": url})
            return {"data": []}

        creds = AttioCredentials(api_key="testkey")
        client = AttioClient(credentials=creds, request_executor=fake)
        tools = create_attio_tools(client=client)
        registry = ToolRegistry(tools)
        result = registry.execute(ATTIO_REQUEST, {"operation": "list_objects"})
        self.assertEqual(result.output["operation"], "list_objects")
        self.assertEqual(len(captured), 1)

    def test_create_attio_tools_raises_without_credentials_or_client(self) -> None:
        with self.assertRaises(ValueError):
            create_attio_tools()

    def test_allowed_operations_subset(self) -> None:
        creds = AttioCredentials(api_key="testkey")
        tools = create_attio_tools(
            credentials=creds,
            allowed_operations=["list_objects", "get_record"],
        )
        enum_vals = tools[0].definition.input_schema["properties"]["operation"]["enum"]
        self.assertEqual(set(enum_vals), {"list_objects", "get_record"})


if __name__ == "__main__":
    unittest.main()
