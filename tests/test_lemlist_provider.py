"""Tests for harnessiq.providers.lemlist."""

from __future__ import annotations

import base64
import unittest

from harnessiq.providers.lemlist import (
    LEMLIST_REQUEST,
    LemlistClient,
    LemlistCredentials,
    build_lemlist_operation_catalog,
    create_lemlist_tools,
    get_lemlist_operation,
)
from harnessiq.tools.registry import ToolRegistry


class LemlistCredentialsTests(unittest.TestCase):
    def test_valid_credentials_accepted(self) -> None:
        c = LemlistCredentials(api_key="key123")
        self.assertEqual(c.api_key, "key123")

    def test_blank_api_key_raises(self) -> None:
        with self.assertRaises(ValueError):
            LemlistCredentials(api_key="")

    def test_blank_api_key_whitespace_raises(self) -> None:
        with self.assertRaises(ValueError):
            LemlistCredentials(api_key="   ")

    def test_zero_timeout_raises(self) -> None:
        with self.assertRaises(ValueError):
            LemlistCredentials(api_key="key", timeout_seconds=0)

    def test_default_base_url_set(self) -> None:
        c = LemlistCredentials(api_key="key")
        self.assertIn("lemlist.com", c.base_url)

    def test_as_redacted_dict_excludes_raw_key(self) -> None:
        c = LemlistCredentials(api_key="supersecretkey")
        summary = c.as_redacted_dict()
        self.assertNotIn("supersecretkey", str(summary))


class LemlistApiTests(unittest.TestCase):
    def test_build_headers_produces_basic_auth_with_empty_username(self) -> None:
        from harnessiq.providers.lemlist.api import build_headers
        headers = build_headers("mykey")
        expected_token = base64.b64encode(b":mykey").decode()
        self.assertEqual(headers["Authorization"], f"Basic {expected_token}")

    def test_basic_auth_username_is_empty(self) -> None:
        from harnessiq.providers.lemlist.api import build_headers
        headers = build_headers("mykey")
        token = headers["Authorization"].split(" ", 1)[1]
        decoded = base64.b64decode(token).decode()
        username, _ = decoded.split(":", 1)
        self.assertEqual(username, "")

    def test_build_headers_with_extra_headers(self) -> None:
        from harnessiq.providers.lemlist.api import build_headers
        headers = build_headers("k", extra_headers={"X-Custom": "val"})
        self.assertEqual(headers["X-Custom"], "val")
        self.assertIn("Authorization", headers)


class LemlistOperationCatalogTests(unittest.TestCase):
    def test_catalog_is_non_empty(self) -> None:
        catalog = build_lemlist_operation_catalog()
        self.assertGreater(len(catalog), 0)

    def test_catalog_covers_core_categories(self) -> None:
        catalog = build_lemlist_operation_catalog()
        categories = {op.category for op in catalog}
        self.assertIn("Campaign", categories)
        self.assertIn("Lead", categories)
        self.assertIn("Hook", categories)

    def test_list_campaigns_is_get(self) -> None:
        op = get_lemlist_operation("list_campaigns")
        self.assertEqual(op.method, "GET")

    def test_create_campaign_requires_payload(self) -> None:
        op = get_lemlist_operation("create_campaign")
        self.assertTrue(op.payload_required)
        self.assertEqual(op.method, "POST")

    def test_get_campaign_requires_campaign_id(self) -> None:
        op = get_lemlist_operation("get_campaign")
        self.assertIn("campaign_id", op.required_path_params)

    def test_add_lead_to_campaign_requires_both_ids(self) -> None:
        op = get_lemlist_operation("add_lead_to_campaign")
        self.assertIn("campaign_id", op.required_path_params)
        self.assertIn("lead_id", op.required_path_params)

    def test_get_operation_raises_for_unknown(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            get_lemlist_operation("nonexistent_op")
        self.assertIn("nonexistent_op", str(ctx.exception))


class LemlistClientTests(unittest.TestCase):
    def _client(self) -> LemlistClient:
        creds = LemlistCredentials(api_key="testkey")
        return LemlistClient(credentials=creds, request_executor=lambda m, u, **kw: {"ok": True})

    def test_prepare_request_list_campaigns_url(self) -> None:
        prepared = self._client().prepare_request("list_campaigns")
        self.assertIn("/campaigns", prepared.url)
        self.assertEqual(prepared.method, "GET")

    def test_prepare_request_interpolates_campaign_id(self) -> None:
        prepared = self._client().prepare_request("get_campaign", path_params={"campaign_id": "camp1"})
        self.assertIn("camp1", prepared.url)

    def test_prepare_request_sets_basic_auth_header(self) -> None:
        prepared = self._client().prepare_request("list_campaigns")
        self.assertIn("Basic ", prepared.headers["Authorization"])

    def test_prepare_request_raises_on_missing_path_param(self) -> None:
        with self.assertRaises(ValueError):
            self._client().prepare_request("get_campaign")

    def test_prepare_request_raises_on_missing_required_payload(self) -> None:
        with self.assertRaises(ValueError):
            self._client().prepare_request("create_campaign")

    def test_prepare_request_rejects_payload_on_no_payload_op(self) -> None:
        with self.assertRaises(ValueError):
            self._client().prepare_request("list_campaigns", payload={"bad": "field"})


class LemlistToolsTests(unittest.TestCase):
    def test_create_lemlist_tools_returns_registerable_tuple(self) -> None:
        creds = LemlistCredentials(api_key="testkey")
        tools = create_lemlist_tools(credentials=creds)
        self.assertEqual(len(tools), 1)
        ToolRegistry(tools)

    def test_tool_definition_key_is_lemlist_request(self) -> None:
        creds = LemlistCredentials(api_key="testkey")
        tools = create_lemlist_tools(credentials=creds)
        self.assertEqual(tools[0].definition.key, LEMLIST_REQUEST)

    def test_tool_handler_executes_list_campaigns(self) -> None:
        captured: list[dict[str, object]] = []

        def fake(method: str, url: str, **kwargs: object) -> dict[str, object]:
            captured.append({"method": method, "url": url})
            return [{"id": "c1"}]

        creds = LemlistCredentials(api_key="testkey")
        client = LemlistClient(credentials=creds, request_executor=fake)
        tools = create_lemlist_tools(client=client)
        registry = ToolRegistry(tools)
        result = registry.execute(LEMLIST_REQUEST, {"operation": "list_campaigns"})
        self.assertEqual(result.output["operation"], "list_campaigns")
        self.assertEqual(len(captured), 1)

    def test_create_lemlist_tools_raises_without_credentials_or_client(self) -> None:
        with self.assertRaises(ValueError):
            create_lemlist_tools()

    def test_allowed_operations_subset(self) -> None:
        creds = LemlistCredentials(api_key="testkey")
        tools = create_lemlist_tools(credentials=creds, allowed_operations=["list_campaigns", "get_campaign"])
        enum_vals = tools[0].definition.input_schema["properties"]["operation"]["enum"]
        self.assertEqual(set(enum_vals), {"list_campaigns", "get_campaign"})


if __name__ == "__main__":
    unittest.main()
