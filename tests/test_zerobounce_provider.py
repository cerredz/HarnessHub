"""Unit tests for the ZeroBounce provider."""

from __future__ import annotations

import unittest

from harnessiq.providers.zerobounce.api import DEFAULT_BASE_URL, DEFAULT_BULK_BASE_URL, build_headers
from harnessiq.providers.zerobounce.client import ZeroBounceClient, ZeroBounceCredentials
from harnessiq.providers.zerobounce.operations import (
    build_zerobounce_operation_catalog,
    build_zerobounce_request_tool_definition,
    create_zerobounce_tools,
    get_zerobounce_operation,
)


def _mock_executor(response: object):
    def executor(method, url, *, headers, json_body, timeout_seconds):
        return response
    return executor


class ZeroBounceCredentialsTests(unittest.TestCase):
    def test_valid_credentials(self):
        creds = ZeroBounceCredentials(api_key="zb-key")
        self.assertEqual(creds.api_key, "zb-key")
        self.assertEqual(creds.base_url, DEFAULT_BASE_URL)
        self.assertEqual(creds.bulk_base_url, DEFAULT_BULK_BASE_URL)
        self.assertEqual(creds.timeout_seconds, 60.0)

    def test_blank_api_key_raises(self):
        with self.assertRaises(ValueError):
            ZeroBounceCredentials(api_key="")

    def test_blank_base_url_raises(self):
        with self.assertRaises(ValueError):
            ZeroBounceCredentials(api_key="k", base_url="")

    def test_blank_bulk_base_url_raises(self):
        with self.assertRaises(ValueError):
            ZeroBounceCredentials(api_key="k", bulk_base_url="")

    def test_zero_timeout_raises(self):
        with self.assertRaises(ValueError):
            ZeroBounceCredentials(api_key="k", timeout_seconds=0)

    def test_masked_api_key_hides_secret(self):
        creds = ZeroBounceCredentials(api_key="abcdefghijklmnop")
        masked = creds.masked_api_key()
        self.assertNotIn("abcdefghijklmnop", masked)
        self.assertTrue(masked.startswith("abc"))

    def test_as_redacted_dict_no_raw_key(self):
        creds = ZeroBounceCredentials(api_key="my-secret-zb-key")
        d = creds.as_redacted_dict()
        self.assertNotIn("my-secret-zb-key", str(d))
        self.assertIn("bulk_base_url", d)


class ZeroBounceApiTests(unittest.TestCase):
    def test_build_headers_no_auth(self):
        headers = build_headers()
        self.assertNotIn("api_key", headers)
        self.assertNotIn("Authorization", headers)
        self.assertEqual(headers["Content-Type"], "application/json")


class ZeroBounceOperationCatalogTests(unittest.TestCase):
    def test_catalog_count(self):
        catalog = build_zerobounce_operation_catalog()
        self.assertEqual(len(catalog), 22)

    def test_operation_names_present(self):
        names = {op.name for op in build_zerobounce_operation_catalog()}
        self.assertIn("get_credits", names)
        self.assertIn("validate_email", names)
        self.assertIn("validate_batch", names)
        self.assertIn("bulk_send_file", names)
        self.assertIn("bulk_file_status", names)
        self.assertIn("bulk_get_file", names)
        self.assertIn("bulk_delete_file", names)
        self.assertIn("score_email", names)
        self.assertIn("find_email", names)
        self.assertIn("get_activity_data", names)
        self.assertIn("list_filters", names)
        self.assertIn("add_filter", names)
        self.assertIn("delete_filter", names)

    def test_bulk_operations_use_bulk_base(self):
        bulk_ops = {"bulk_send_file", "bulk_file_status", "bulk_get_file", "bulk_delete_file",
                    "bulk_scoring_send_file", "bulk_scoring_file_status", "bulk_scoring_get_file",
                    "bulk_scoring_delete_file", "bulk_finder_send_file", "bulk_finder_file_status",
                    "bulk_finder_get_file", "bulk_finder_delete_file"}
        for name in bulk_ops:
            op = get_zerobounce_operation(name)
            self.assertTrue(op.use_bulk_base, f"{name} should use bulk base URL")

    def test_standard_operations_use_standard_base(self):
        standard_ops = {"get_credits", "validate_email", "validate_batch", "score_email", "find_email"}
        for name in standard_ops:
            op = get_zerobounce_operation(name)
            self.assertFalse(op.use_bulk_base, f"{name} should not use bulk base URL")

    def test_get_invalid_operation_raises(self):
        with self.assertRaises(ValueError) as ctx:
            get_zerobounce_operation("nonexistent")
        self.assertIn("nonexistent", str(ctx.exception))


class ZeroBounceClientTests(unittest.TestCase):
    def _make_client(self, response=None):
        creds = ZeroBounceCredentials(api_key="zb-test-key")
        return ZeroBounceClient(
            credentials=creds,
            request_executor=_mock_executor(response or {"status": "ok"}),
        )

    def test_api_key_in_url_as_query_param(self):
        client = self._make_client()
        prepared = client.prepare_request("validate_email", query={"email": "test@test.com"})
        self.assertIn("api_key=zb-test-key", prepared.url)

    def test_api_key_not_in_headers(self):
        client = self._make_client()
        prepared = client.prepare_request("validate_email", query={"email": "test@test.com"})
        self.assertNotIn("api_key", prepared.headers)

    def test_standard_op_uses_standard_base_url(self):
        client = self._make_client()
        prepared = client.prepare_request("validate_email", query={"email": "test@test.com"})
        self.assertIn("api.zerobounce.net", prepared.url)
        self.assertNotIn("bulkapi", prepared.url)

    def test_bulk_op_uses_bulk_base_url(self):
        client = self._make_client()
        prepared = client.prepare_request("bulk_send_file", payload={"email_address_column": 1})
        self.assertIn("bulkapi.zerobounce.net", prepared.url)

    def test_validate_batch_requires_payload(self):
        client = self._make_client()
        with self.assertRaises(ValueError) as ctx:
            client.prepare_request("validate_batch")
        self.assertIn("requires a payload", str(ctx.exception))

    def test_validate_email_does_not_accept_payload(self):
        client = self._make_client()
        with self.assertRaises(ValueError):
            client.prepare_request("validate_email", payload={"bad": "data"})

    def test_execute_operation_returns_response(self):
        response = {"status": "valid", "email_address": "test@test.com"}
        client = self._make_client(response=response)
        result = client.execute_operation("validate_email", query={"email": "test@test.com"})
        self.assertEqual(result, response)


class ZeroBounceToolTests(unittest.TestCase):
    def _make_creds(self):
        return ZeroBounceCredentials(api_key="zb-tool-key")

    def test_create_tools_returns_one_tool(self):
        tools = create_zerobounce_tools(credentials=self._make_creds())
        self.assertEqual(len(tools), 1)

    def test_tool_key(self):
        tools = create_zerobounce_tools(credentials=self._make_creds())
        self.assertEqual(tools[0].key, "zerobounce.request")

    def test_tool_name(self):
        tools = create_zerobounce_tools(credentials=self._make_creds())
        self.assertEqual(tools[0].definition.name, "zerobounce_request")

    def test_no_credentials_raises(self):
        with self.assertRaises(ValueError):
            create_zerobounce_tools()

    def test_handler_returns_expected_shape(self):
        response = {"status": "valid"}
        creds = self._make_creds()
        client = ZeroBounceClient(
            credentials=creds,
            request_executor=_mock_executor(response),
        )
        tools = create_zerobounce_tools(client=client)
        result = tools[0].handler({"operation": "validate_email", "query": {"email": "x@x.com"}})
        self.assertIn("operation", result)
        self.assertIn("response", result)
        self.assertEqual(result["response"], response)

    def test_tool_definition_required_operation(self):
        defn = build_zerobounce_request_tool_definition()
        self.assertIn("operation", defn.input_schema["required"])


if __name__ == "__main__":
    unittest.main()
