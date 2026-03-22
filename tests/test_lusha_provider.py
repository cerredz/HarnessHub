"""Unit tests for the Lusha provider."""

from __future__ import annotations

import unittest

from harnessiq.providers.lusha.api import DEFAULT_BASE_URL, build_headers
from harnessiq.providers.lusha.client import LushaClient, LushaCredentials
from harnessiq.providers.lusha.operations import (
    build_lusha_operation_catalog,
    build_lusha_request_tool_definition,
    create_lusha_tools,
    get_lusha_operation,
)


def _mock_executor(response: object):
    def executor(method, url, *, headers, json_body, timeout_seconds):
        return response
    return executor


class LushaCredentialsTests(unittest.TestCase):
    def test_valid_credentials(self):
        creds = LushaCredentials(api_key="lusha-key-123")
        self.assertEqual(creds.api_key, "lusha-key-123")
        self.assertEqual(creds.base_url, DEFAULT_BASE_URL)
        self.assertEqual(creds.timeout_seconds, 60.0)

    def test_blank_api_key_raises(self):
        with self.assertRaises(ValueError):
            LushaCredentials(api_key="")

    def test_whitespace_api_key_raises(self):
        with self.assertRaises(ValueError):
            LushaCredentials(api_key="   ")

    def test_blank_base_url_raises(self):
        with self.assertRaises(ValueError):
            LushaCredentials(api_key="k", base_url="")

    def test_zero_timeout_raises(self):
        with self.assertRaises(ValueError):
            LushaCredentials(api_key="k", timeout_seconds=0)

    def test_masked_api_key_hides_secret(self):
        creds = LushaCredentials(api_key="abcdefghijklmnop")
        masked = creds.masked_api_key()
        self.assertNotIn("abcdefghijklmnop", masked)
        self.assertTrue(masked.startswith("abc"))

    def test_as_redacted_dict_no_raw_key(self):
        creds = LushaCredentials(api_key="my-secret-lusha-key")
        d = creds.as_redacted_dict()
        self.assertNotIn("my-secret-lusha-key", str(d))
        self.assertIn("api_key_masked", d)


class LushaApiTests(unittest.TestCase):
    def test_build_headers_lowercase_api_key(self):
        """Lusha requires lowercase 'api_key' header name (case-sensitive)."""
        headers = build_headers("my-key")
        self.assertEqual(headers["api_key"], "my-key")
        # Must NOT use X-Api-Key or Authorization
        self.assertNotIn("X-Api-Key", headers)
        self.assertNotIn("Authorization", headers)

    def test_build_headers_content_type(self):
        headers = build_headers("k")
        self.assertEqual(headers["Content-Type"], "application/json")

    def test_build_headers_extra(self):
        headers = build_headers("k", extra_headers={"X-Custom": "value"})
        self.assertEqual(headers["X-Custom"], "value")


class LushaOperationCatalogTests(unittest.TestCase):
    def test_catalog_count(self):
        catalog = build_lusha_operation_catalog()
        self.assertEqual(len(catalog), 40)

    def test_enrichment_operations_present(self):
        names = {op.name for op in build_lusha_operation_catalog()}
        self.assertIn("enrich_person", names)
        self.assertIn("bulk_enrich_persons", names)
        self.assertIn("enrich_company", names)
        self.assertIn("bulk_enrich_companies", names)

    def test_prospecting_operations_present(self):
        names = {op.name for op in build_lusha_operation_catalog()}
        self.assertIn("search_contacts", names)
        self.assertIn("enrich_contacts", names)
        self.assertIn("search_companies", names)
        self.assertIn("enrich_companies", names)

    def test_filter_operations_present(self):
        names = {op.name for op in build_lusha_operation_catalog()}
        self.assertIn("get_contact_departments", names)
        self.assertIn("get_contact_seniority_levels", names)
        self.assertIn("get_industry_labels", names)
        self.assertIn("search_technologies", names)

    def test_signal_operations_present(self):
        names = {op.name for op in build_lusha_operation_catalog()}
        self.assertIn("get_signal_filters", names)
        self.assertIn("get_contact_signals", names)
        self.assertIn("search_contact_signals", names)
        self.assertIn("get_company_signals", names)

    def test_lookalike_operations_present(self):
        names = {op.name for op in build_lusha_operation_catalog()}
        self.assertIn("find_similar_contacts", names)
        self.assertIn("find_similar_companies", names)

    def test_webhook_operations_present(self):
        names = {op.name for op in build_lusha_operation_catalog()}
        self.assertIn("create_subscriptions", names)
        self.assertIn("list_subscriptions", names)
        self.assertIn("get_subscription", names)
        self.assertIn("update_subscription", names)
        self.assertIn("delete_subscriptions", names)
        self.assertIn("test_subscription", names)
        self.assertIn("get_webhook_audit_logs", names)
        self.assertIn("get_webhook_secret", names)
        self.assertIn("regenerate_webhook_secret", names)

    def test_account_operations_present(self):
        names = {op.name for op in build_lusha_operation_catalog()}
        self.assertIn("get_account_usage", names)

    def test_get_invalid_operation_raises(self):
        with self.assertRaises(ValueError) as ctx:
            get_lusha_operation("nonexistent")
        self.assertIn("nonexistent", str(ctx.exception))

    def test_signal_filters_requires_object_type(self):
        op = get_lusha_operation("get_signal_filters")
        self.assertIn("object_type", op.required_path_params)

    def test_get_subscription_requires_subscription_id(self):
        op = get_lusha_operation("get_subscription")
        self.assertIn("subscription_id", op.required_path_params)

    def test_enrich_person_uses_get(self):
        op = get_lusha_operation("enrich_person")
        self.assertEqual(op.method, "GET")
        self.assertTrue(op.allow_query)

    def test_bulk_enrich_persons_uses_post(self):
        op = get_lusha_operation("bulk_enrich_persons")
        self.assertEqual(op.method, "POST")

    def test_bulk_enrich_companies_path(self):
        op = get_lusha_operation("bulk_enrich_companies")
        self.assertEqual(op.path_hint, "/bulk/company/v2")


class LushaClientTests(unittest.TestCase):
    def _make_client(self, response=None):
        creds = LushaCredentials(api_key="lusha-test-key")
        return LushaClient(
            credentials=creds,
            request_executor=_mock_executor(response or {}),
        )

    def test_api_key_in_headers(self):
        client = self._make_client()
        prepared = client.prepare_request("enrich_person", query={"firstName": "John", "companyDomain": "acme.com"})
        self.assertEqual(prepared.headers["api_key"], "lusha-test-key")

    def test_api_key_not_in_url(self):
        client = self._make_client()
        prepared = client.prepare_request("enrich_person", query={"firstName": "John", "companyDomain": "acme.com"})
        self.assertNotIn("api_key=", prepared.url)

    def test_base_url_is_lusha(self):
        client = self._make_client()
        prepared = client.prepare_request("get_account_usage")
        self.assertIn("api.lusha.com", prepared.url)

    def test_missing_object_type_raises(self):
        client = self._make_client()
        with self.assertRaises(ValueError) as ctx:
            client.prepare_request("get_signal_filters")
        self.assertIn("object_type", str(ctx.exception))

    def test_object_type_path_substituted(self):
        client = self._make_client()
        prepared = client.prepare_request(
            "get_signal_filters",
            path_params={"object_type": "contact"},
        )
        self.assertIn("contact", prepared.url)
        self.assertNotIn("{object_type}", prepared.url)

    def test_bulk_enrich_persons_requires_payload(self):
        client = self._make_client()
        with self.assertRaises(ValueError):
            client.prepare_request("bulk_enrich_persons")

    def test_search_contacts_requires_payload(self):
        client = self._make_client()
        with self.assertRaises(ValueError):
            client.prepare_request("search_contacts")

    def test_get_account_usage_no_payload_accepted(self):
        client = self._make_client()
        with self.assertRaises(ValueError):
            client.prepare_request("get_account_usage", payload={"bad": "data"})

    def test_execute_returns_response(self):
        response = {"total": 100, "used": 25, "remaining": 75}
        client = self._make_client(response=response)
        result = client.execute_operation("get_account_usage")
        self.assertEqual(result, response)


class LushaToolTests(unittest.TestCase):
    def _make_creds(self):
        return LushaCredentials(api_key="lusha-tool-key")

    def test_create_tools_returns_one_tool(self):
        tools = create_lusha_tools(credentials=self._make_creds())
        self.assertEqual(len(tools), 1)

    def test_tool_key(self):
        tools = create_lusha_tools(credentials=self._make_creds())
        self.assertEqual(tools[0].key, "lusha.request")

    def test_tool_name(self):
        tools = create_lusha_tools(credentials=self._make_creds())
        self.assertEqual(tools[0].definition.name, "lusha_request")

    def test_no_credentials_raises(self):
        with self.assertRaises(ValueError):
            create_lusha_tools()

    def test_handler_returns_expected_shape(self):
        response = {"total": 100}
        creds = self._make_creds()
        client = LushaClient(
            credentials=creds,
            request_executor=_mock_executor(response),
        )
        tools = create_lusha_tools(client=client)
        result = tools[0].handler({"operation": "get_account_usage"})
        self.assertIn("operation", result)
        self.assertIn("response", result)
        self.assertEqual(result["response"], response)

    def test_handler_invalid_operation_raises(self):
        tools = create_lusha_tools(credentials=self._make_creds())
        with self.assertRaises(ValueError):
            tools[0].handler({"operation": "invalid_op"})

    def test_tool_definition_required_operation(self):
        defn = build_lusha_request_tool_definition()
        self.assertIn("operation", defn.input_schema["required"])

    def test_allowed_operations_filters_catalog(self):
        tools = create_lusha_tools(
            credentials=self._make_creds(),
            allowed_operations=["enrich_person", "enrich_company"],
        )
        schema = tools[0].definition.input_schema
        self.assertEqual(schema["properties"]["operation"]["enum"], ["enrich_person", "enrich_company"])


if __name__ == "__main__":
    unittest.main()
