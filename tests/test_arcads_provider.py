"""Tests for harnessiq.providers.arcads."""

from __future__ import annotations

import base64
import unittest

from harnessiq.providers.arcads import (
    ArcadsClient,
    ArcadsCredentials,
    build_arcads_operation_catalog,
    get_arcads_operation,
)
from harnessiq.shared.tools import ARCADS_REQUEST
from harnessiq.tools.arcads import create_arcads_tools
from harnessiq.tools.registry import ToolRegistry


class ArcadsCredentialsTests(unittest.TestCase):
    def test_valid_credentials_accepted(self) -> None:
        c = ArcadsCredentials(client_id="cid", client_secret="csec")
        self.assertEqual(c.client_id, "cid")

    def test_blank_client_id_raises(self) -> None:
        with self.assertRaises(ValueError):
            ArcadsCredentials(client_id="", client_secret="sec")

    def test_blank_client_secret_raises(self) -> None:
        with self.assertRaises(ValueError):
            ArcadsCredentials(client_id="cid", client_secret="")

    def test_zero_timeout_raises(self) -> None:
        with self.assertRaises(ValueError):
            ArcadsCredentials(client_id="cid", client_secret="sec", timeout_seconds=0)

    def test_masked_secret_redacts_middle(self) -> None:
        c = ArcadsCredentials(client_id="cid", client_secret="abcdefghijklmn")
        masked = c.masked_client_secret()
        self.assertIn("*", masked)
        self.assertNotIn("defghij", masked)

    def test_as_redacted_dict_excludes_raw_secret(self) -> None:
        c = ArcadsCredentials(client_id="cid", client_secret="supersecret")
        summary = c.as_redacted_dict()
        self.assertNotIn("supersecret", str(summary))
        self.assertIn("client_secret_masked", summary)


class ArcadsApiTests(unittest.TestCase):
    def test_build_headers_produces_basic_auth(self) -> None:
        from harnessiq.providers.arcads.api import build_headers
        headers = build_headers("mycid", "mysecret")
        expected_token = base64.b64encode(b"mycid:mysecret").decode()
        self.assertEqual(headers["Authorization"], f"Basic {expected_token}")

    def test_build_headers_with_extra_headers(self) -> None:
        from harnessiq.providers.arcads.api import build_headers
        headers = build_headers("cid", "sec", extra_headers={"X-Custom": "value"})
        self.assertEqual(headers["X-Custom"], "value")
        self.assertIn("Authorization", headers)


class ArcadsOperationCatalogTests(unittest.TestCase):
    def test_catalog_covers_all_categories(self) -> None:
        catalog = build_arcads_operation_catalog()
        categories = {op.category for op in catalog}
        self.assertEqual(categories, {"Products", "Folders", "Situations", "Scripts", "Videos"})

    def test_catalog_has_correct_operation_count(self) -> None:
        catalog = build_arcads_operation_catalog()
        self.assertEqual(len(catalog), 10)

    def test_generate_video_requires_script_id(self) -> None:
        op = get_arcads_operation("generate_video")
        self.assertIn("scriptId", op.required_path_params)
        self.assertEqual(op.method, "POST")

    def test_list_situations_allows_query(self) -> None:
        op = get_arcads_operation("list_situations")
        self.assertTrue(op.allow_query)

    def test_get_operation_raises_for_unknown(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            get_arcads_operation("nonexistent")
        self.assertIn("nonexistent", str(ctx.exception))


class ArcadsClientTests(unittest.TestCase):
    def _client(self) -> ArcadsClient:
        creds = ArcadsCredentials(client_id="cid", client_secret="sec")
        return ArcadsClient(credentials=creds, request_executor=lambda m, u, **kw: {"ok": True})

    def test_prepare_request_list_products_url(self) -> None:
        prepared = self._client().prepare_request("list_products")
        self.assertIn("/v1/products", prepared.url)
        self.assertEqual(prepared.method, "GET")

    def test_prepare_request_interpolates_product_id(self) -> None:
        prepared = self._client().prepare_request("list_product_folders", path_params={"productId": "p123"})
        self.assertIn("p123", prepared.url)

    def test_prepare_request_sets_basic_auth_header(self) -> None:
        prepared = self._client().prepare_request("list_products")
        self.assertIn("Basic ", prepared.headers["Authorization"])

    def test_prepare_request_raises_on_missing_path_param(self) -> None:
        with self.assertRaises(ValueError):
            self._client().prepare_request("list_product_folders")

    def test_prepare_request_raises_on_missing_required_payload(self) -> None:
        with self.assertRaises(ValueError):
            self._client().prepare_request("create_product")

    def test_generate_video_optional_payload_accepted(self) -> None:
        # generate_video has payload_kind="object" but payload_required=False
        prepared = self._client().prepare_request(
            "generate_video",
            path_params={"scriptId": "s1"},
        )
        self.assertIsNone(prepared.json_body)


class ArcadsToolsTests(unittest.TestCase):
    def test_create_arcads_tools_returns_registerable_tuple(self) -> None:
        creds = ArcadsCredentials(client_id="cid", client_secret="sec")
        tools = create_arcads_tools(credentials=creds)
        self.assertEqual(len(tools), 1)
        ToolRegistry(tools)

    def test_tool_handler_executes_list_products(self) -> None:
        captured: list[dict[str, object]] = []

        def fake(method: str, url: str, **kwargs: object) -> dict[str, object]:
            captured.append({"method": method, "url": url})
            return [{"id": "p1"}]

        creds = ArcadsCredentials(client_id="cid", client_secret="sec")
        client = ArcadsClient(credentials=creds, request_executor=fake)
        tools = create_arcads_tools(client=client)
        registry = ToolRegistry(tools)
        result = registry.execute(ARCADS_REQUEST, {"operation": "list_products"})
        self.assertEqual(result.output["operation"], "list_products")

    def test_create_arcads_tools_raises_without_credentials_or_client(self) -> None:
        with self.assertRaises(ValueError):
            create_arcads_tools()


if __name__ == "__main__":
    unittest.main()
