"""Tests for harnessiq.providers.outreach."""

from __future__ import annotations

import unittest

from harnessiq.providers.outreach import (
    OutreachClient,
    OutreachCredentials,
    build_outreach_operation_catalog,
    get_outreach_operation,
)
from harnessiq.shared.tools import OUTREACH_REQUEST
from harnessiq.tools.outreach import create_outreach_tools
from harnessiq.tools.registry import ToolRegistry


class OutreachCredentialsTests(unittest.TestCase):
    def test_valid_credentials_accepted(self) -> None:
        c = OutreachCredentials(access_token="tok123")
        self.assertEqual(c.access_token, "tok123")

    def test_blank_access_token_raises(self) -> None:
        with self.assertRaises(ValueError):
            OutreachCredentials(access_token="")

    def test_blank_access_token_whitespace_raises(self) -> None:
        with self.assertRaises(ValueError):
            OutreachCredentials(access_token="   ")

    def test_zero_timeout_raises(self) -> None:
        with self.assertRaises(ValueError):
            OutreachCredentials(access_token="tok", timeout_seconds=0)

    def test_default_base_url_set(self) -> None:
        c = OutreachCredentials(access_token="tok")
        self.assertIn("outreach.io", c.base_url)

    def test_masked_access_token_redacts_middle(self) -> None:
        c = OutreachCredentials(access_token="abcdefghijklmn")
        masked = c.masked_access_token()
        self.assertIn("*", masked)
        self.assertNotIn("defghij", masked)

    def test_as_redacted_dict_excludes_raw_token(self) -> None:
        c = OutreachCredentials(access_token="supersecrettoken")
        summary = c.as_redacted_dict()
        self.assertNotIn("supersecrettoken", str(summary))
        self.assertIn("access_token_masked", summary)


class OutreachApiTests(unittest.TestCase):
    def test_build_headers_produces_bearer_token(self) -> None:
        from harnessiq.providers.outreach.api import build_headers
        headers = build_headers("mytoken")
        self.assertEqual(headers["Authorization"], "Bearer mytoken")

    def test_build_headers_with_extra_headers(self) -> None:
        from harnessiq.providers.outreach.api import build_headers
        headers = build_headers("tok", extra_headers={"X-Custom": "val"})
        self.assertEqual(headers["X-Custom"], "val")
        self.assertIn("Authorization", headers)


class OutreachOperationCatalogTests(unittest.TestCase):
    def test_catalog_is_non_empty(self) -> None:
        catalog = build_outreach_operation_catalog()
        self.assertGreater(len(catalog), 0)

    def test_catalog_covers_core_categories(self) -> None:
        catalog = build_outreach_operation_catalog()
        categories = {op.category for op in catalog}
        self.assertIn("Prospect", categories)
        self.assertIn("Account", categories)
        self.assertIn("Sequence", categories)
        self.assertIn("Webhook", categories)
        self.assertIn("User", categories)

    def test_list_prospects_allows_query(self) -> None:
        op = get_outreach_operation("list_prospects")
        self.assertTrue(op.allow_query)
        self.assertEqual(op.method, "GET")

    def test_create_prospect_requires_payload(self) -> None:
        op = get_outreach_operation("create_prospect")
        self.assertTrue(op.payload_required)
        self.assertEqual(op.method, "POST")

    def test_get_prospect_requires_prospect_id(self) -> None:
        op = get_outreach_operation("get_prospect")
        self.assertIn("prospect_id", op.required_path_params)

    def test_get_operation_raises_for_unknown(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            get_outreach_operation("nonexistent_op")
        self.assertIn("nonexistent_op", str(ctx.exception))


class OutreachClientTests(unittest.TestCase):
    def _client(self) -> OutreachClient:
        creds = OutreachCredentials(access_token="testtoken")
        return OutreachClient(credentials=creds, request_executor=lambda m, u, **kw: {"ok": True})

    def test_prepare_request_list_prospects_url(self) -> None:
        prepared = self._client().prepare_request("list_prospects")
        self.assertIn("/prospects", prepared.url)
        self.assertEqual(prepared.method, "GET")

    def test_prepare_request_interpolates_prospect_id(self) -> None:
        prepared = self._client().prepare_request("get_prospect", path_params={"prospect_id": "p42"})
        self.assertIn("p42", prepared.url)

    def test_prepare_request_sets_bearer_header(self) -> None:
        prepared = self._client().prepare_request("list_prospects")
        self.assertEqual(prepared.headers["Authorization"], "Bearer testtoken")

    def test_prepare_request_raises_on_missing_path_param(self) -> None:
        with self.assertRaises(ValueError):
            self._client().prepare_request("get_prospect")

    def test_prepare_request_raises_on_missing_required_payload(self) -> None:
        with self.assertRaises(ValueError):
            self._client().prepare_request("create_prospect")

    def test_prepare_request_rejects_payload_on_no_payload_op(self) -> None:
        with self.assertRaises(ValueError):
            self._client().prepare_request("list_prospects", payload={"bad": "field"})


class OutreachToolsTests(unittest.TestCase):
    def test_create_outreach_tools_returns_registerable_tuple(self) -> None:
        creds = OutreachCredentials(access_token="testtoken")
        tools = create_outreach_tools(credentials=creds)
        self.assertEqual(len(tools), 1)
        ToolRegistry(tools)

    def test_tool_definition_key_is_outreach_request(self) -> None:
        creds = OutreachCredentials(access_token="testtoken")
        tools = create_outreach_tools(credentials=creds)
        self.assertEqual(tools[0].definition.key, OUTREACH_REQUEST)

    def test_tool_handler_executes_list_prospects(self) -> None:
        captured: list[dict[str, object]] = []

        def fake(method: str, url: str, **kwargs: object) -> dict[str, object]:
            captured.append({"method": method, "url": url})
            return [{"id": "p1"}]

        creds = OutreachCredentials(access_token="testtoken")
        client = OutreachClient(credentials=creds, request_executor=fake)
        tools = create_outreach_tools(client=client)
        registry = ToolRegistry(tools)
        result = registry.execute(OUTREACH_REQUEST, {"operation": "list_prospects"})
        self.assertEqual(result.output["operation"], "list_prospects")
        self.assertEqual(len(captured), 1)

    def test_create_outreach_tools_raises_without_credentials_or_client(self) -> None:
        with self.assertRaises(ValueError):
            create_outreach_tools()

    def test_allowed_operations_subset(self) -> None:
        creds = OutreachCredentials(access_token="testtoken")
        tools = create_outreach_tools(credentials=creds, allowed_operations=["list_prospects", "get_prospect"])
        enum_vals = tools[0].definition.input_schema["properties"]["operation"]["enum"]
        self.assertEqual(set(enum_vals), {"list_prospects", "get_prospect"})


if __name__ == "__main__":
    unittest.main()
