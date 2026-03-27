"""Tests for harnessiq.providers.hunter."""

from __future__ import annotations

import unittest

from harnessiq.config.provider_credentials.catalog import PROVIDER_CREDENTIAL_SPECS
from harnessiq.providers.hunter import HUNTER_BASE_URL, HunterClient, HunterCredentials
from harnessiq.providers.hunter.api import DEFAULT_BASE_URL, build_headers
from harnessiq.providers.hunter.operations import (
    HUNTER_REQUEST,
    build_hunter_operation_catalog,
    build_hunter_request_tool_definition,
    create_hunter_tools,
    get_hunter_operation,
)
from harnessiq.toolset import ToolsetRegistry
from harnessiq.toolset.catalog_provider import (
    PROVIDER_ENTRIES,
    PROVIDER_ENTRY_INDEX,
    PROVIDER_FACTORY_MAP,
)
from harnessiq.tools.hunter import create_hunter_tools as create_hunter_tools_from_tools
from harnessiq.tools.registry import ToolRegistry


def _mock_executor(response: object):
    def executor(method, url, *, headers, json_body, timeout_seconds):
        return response

    return executor


class HunterCredentialsTests(unittest.TestCase):
    def test_valid_credentials(self):
        credentials = HunterCredentials(api_key="hunter-key")

        self.assertEqual(credentials.api_key, "hunter-key")
        self.assertEqual(credentials.base_url, DEFAULT_BASE_URL)
        self.assertEqual(credentials.timeout_seconds, 60.0)

    def test_blank_api_key_raises(self):
        with self.assertRaises(ValueError):
            HunterCredentials(api_key="")

    def test_whitespace_api_key_raises(self):
        with self.assertRaises(ValueError):
            HunterCredentials(api_key="   ")

    def test_zero_timeout_raises(self):
        with self.assertRaises(ValueError):
            HunterCredentials(api_key="hunter-key", timeout_seconds=0)

    def test_negative_timeout_raises(self):
        with self.assertRaises(ValueError):
            HunterCredentials(api_key="hunter-key", timeout_seconds=-1)

    def test_masked_api_key_hides_secret(self):
        credentials = HunterCredentials(api_key="abcdefghijklmnop")
        masked = credentials.masked_api_key()

        self.assertNotIn("abcdefghijklmnop", masked)
        self.assertTrue(masked.startswith("abc"))

    def test_as_redacted_dict_hides_raw_key(self):
        credentials = HunterCredentials(api_key="super-secret-hunter")
        payload = credentials.as_redacted_dict()

        self.assertNotIn("super-secret-hunter", str(payload))
        self.assertEqual(payload["api_key_masked"], credentials.masked_api_key())


class HunterApiTests(unittest.TestCase):
    def test_build_headers_no_auth_header(self):
        headers = build_headers()

        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertNotIn("Authorization", headers)
        self.assertNotIn("X-API-KEY", headers)


class HunterOperationCatalogTests(unittest.TestCase):
    def test_catalog_count(self):
        catalog = build_hunter_operation_catalog()
        self.assertEqual(len(catalog), 14)

    def test_expected_operation_names_present(self):
        names = {operation.name for operation in build_hunter_operation_catalog()}
        self.assertEqual(
            names,
            {
                "domain_search",
                "email_finder",
                "email_verifier",
                "email_count",
                "discover",
                "email_enrichment",
                "company_enrichment",
                "account_info",
                "leads_list",
                "lead_get",
                "lead_create",
                "lead_update",
                "lead_delete",
                "campaigns_list",
            },
        )

    def test_get_unknown_operation_raises(self):
        with self.assertRaises(ValueError) as ctx:
            get_hunter_operation("nonexistent")

        self.assertIn("nonexistent", str(ctx.exception))


class HunterClientTests(unittest.TestCase):
    def _make_client(self, response=None):
        credentials = HunterCredentials(api_key="hunter-test-key")
        return HunterClient(
            credentials=credentials,
            request_executor=_mock_executor(response or {"ok": True}),
        )

    def test_api_key_is_injected_into_query(self):
        prepared = self._make_client().prepare_request(
            "email_verifier",
            query={"email": "person@example.com"},
        )

        self.assertIn("api_key=hunter-test-key", prepared.url)

    def test_api_key_is_not_put_in_headers(self):
        prepared = self._make_client().prepare_request(
            "email_verifier",
            query={"email": "person@example.com"},
        )

        self.assertNotIn("api_key", prepared.headers)
        self.assertNotIn("X-API-KEY", prepared.headers)

    def test_domain_search_requires_domain_or_company(self):
        with self.assertRaises(ValueError) as ctx:
            self._make_client().prepare_request("domain_search")

        self.assertIn("domain", str(ctx.exception))

    def test_domain_search_accepts_domain(self):
        prepared = self._make_client().prepare_request(
            "domain_search",
            query={"domain": "stripe.com"},
        )

        self.assertIn("domain=stripe.com", prepared.url)
        self.assertIsNone(prepared.json_body)

    def test_domain_search_accepts_company(self):
        prepared = self._make_client().prepare_request(
            "domain_search",
            query={"company": "Stripe"},
        )

        self.assertIn("company=Stripe", prepared.url)

    def test_email_finder_requires_name_fields(self):
        with self.assertRaises(ValueError) as ctx:
            self._make_client().prepare_request(
                "email_finder",
                query={"domain": "stripe.com"},
            )

        self.assertIn("full_name", str(ctx.exception))

    def test_email_finder_requires_both_first_and_last_name_when_full_name_missing(self):
        with self.assertRaises(ValueError) as ctx:
            self._make_client().prepare_request(
                "email_finder",
                query={"domain": "stripe.com", "first_name": "Jane"},
            )

        self.assertIn("first_name + last_name", str(ctx.exception))

    def test_email_finder_accepts_first_and_last_name(self):
        prepared = self._make_client().prepare_request(
            "email_finder",
            query={
                "domain": "stripe.com",
                "first_name": "Jane",
                "last_name": "Doe",
            },
        )

        self.assertIn("first_name=Jane", prepared.url)
        self.assertIn("last_name=Doe", prepared.url)

    def test_email_finder_accepts_full_name(self):
        prepared = self._make_client().prepare_request(
            "email_finder",
            query={"company": "Stripe", "full_name": "Jane Doe"},
        )

        self.assertIn("full_name=Jane+Doe", prepared.url)

    def test_email_verifier_requires_email(self):
        with self.assertRaises(ValueError):
            self._make_client().prepare_request("email_verifier")

    def test_lead_get_interpolates_path_param(self):
        prepared = self._make_client().prepare_request(
            "lead_get",
            path_params={"id": "123"},
        )

        self.assertIn("/leads/123", prepared.url)
        self.assertEqual(prepared.path, "/leads/123")

    def test_lead_update_interpolates_path_param(self):
        prepared = self._make_client().prepare_request(
            "lead_update",
            path_params={"id": "456"},
            payload={"email": "person@example.com"},
        )

        self.assertEqual(prepared.path, "/leads/456")

    def test_lead_delete_interpolates_path_param(self):
        prepared = self._make_client().prepare_request(
            "lead_delete",
            path_params={"id": "789"},
        )

        self.assertEqual(prepared.path, "/leads/789")

    def test_lead_create_requires_payload(self):
        with self.assertRaises(ValueError):
            self._make_client().prepare_request("lead_create")

    def test_get_operations_reject_payload(self):
        with self.assertRaises(ValueError):
            self._make_client().prepare_request(
                "domain_search",
                query={"domain": "stripe.com"},
                payload={"bad": True},
            )

    def test_post_operations_store_payload_in_json_body(self):
        prepared = self._make_client().prepare_request(
            "lead_create",
            payload={"email": "person@example.com", "first_name": "Jane"},
        )

        self.assertEqual(prepared.json_body["email"], "person@example.com")
        self.assertIn("api_key=hunter-test-key", prepared.url)

    def test_execute_operation_returns_response(self):
        response = {"data": {"email": "person@example.com"}}
        client = self._make_client(response=response)

        result = client.execute_operation(
            "email_verifier",
            query={"email": "person@example.com"},
        )

        self.assertEqual(result, response)


class HunterToolTests(unittest.TestCase):
    def _make_credentials(self):
        return HunterCredentials(api_key="hunter-tool-key")

    def test_create_tools_returns_one_tool(self):
        tools = create_hunter_tools(credentials=self._make_credentials())
        self.assertEqual(len(tools), 1)

    def test_tool_key_matches_constant(self):
        tools = create_hunter_tools(credentials=self._make_credentials())
        self.assertEqual(tools[0].key, HUNTER_REQUEST)

    def test_tool_module_exports_factory(self):
        tools = create_hunter_tools_from_tools(credentials=self._make_credentials())
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0].key, HUNTER_REQUEST)

    def test_no_credentials_or_client_raises(self):
        with self.assertRaises(ValueError):
            create_hunter_tools()

    def test_handler_returns_expected_shape(self):
        response = {"data": {"status": "valid"}}
        client = HunterClient(
            credentials=self._make_credentials(),
            request_executor=_mock_executor(response),
        )
        registry = ToolRegistry(create_hunter_tools(client=client))

        result = registry.execute(
            HUNTER_REQUEST,
            {
                "operation": "email_verifier",
                "query": {"email": "person@example.com"},
            },
        )

        self.assertEqual(result.output["operation"], "email_verifier")
        self.assertEqual(result.output["response"], response)
        self.assertEqual(result.output["path"], "/email-verifier")

    def test_tool_definition_requires_operation(self):
        definition = build_hunter_request_tool_definition()
        self.assertIn("operation", definition.input_schema["required"])

    def test_allowed_operations_subset_filters_enum(self):
        tools = create_hunter_tools(
            credentials=self._make_credentials(),
            allowed_operations=["domain_search", "email_verifier"],
        )

        enum_values = tools[0].definition.input_schema["properties"]["operation"]["enum"]
        self.assertEqual(set(enum_values), {"domain_search", "email_verifier"})

    def test_allowed_operations_runtime_rejects_other_operations(self):
        tools = create_hunter_tools(
            credentials=self._make_credentials(),
            allowed_operations=["domain_search"],
        )

        with self.assertRaises(ValueError) as ctx:
            tools[0].handler(
                {
                    "operation": "email_verifier",
                    "query": {"email": "person@example.com"},
                }
            )

        self.assertIn("email_verifier", str(ctx.exception))


class HunterCatalogIntegrationTests(unittest.TestCase):
    def test_hunter_request_constant(self):
        self.assertEqual(HUNTER_REQUEST, "hunter.request")

    def test_hunter_base_url_export(self):
        self.assertEqual(HUNTER_BASE_URL, "https://api.hunter.io/v2")

    def test_provider_credential_spec_registered(self):
        self.assertIn("hunter", PROVIDER_CREDENTIAL_SPECS)

    def test_provider_entry_registered(self):
        self.assertIn("hunter.request", PROVIDER_ENTRY_INDEX)
        self.assertEqual(PROVIDER_ENTRY_INDEX["hunter.request"].family, "hunter")

    def test_provider_factory_registered(self):
        self.assertEqual(
            PROVIDER_FACTORY_MAP["hunter"],
            ("harnessiq.tools.hunter", "create_hunter_tools"),
        )

    def test_provider_entries_contain_hunter(self):
        self.assertTrue(any(entry.key == "hunter.request" for entry in PROVIDER_ENTRIES))

    def test_toolset_registry_can_resolve_hunter_tool(self):
        registry = ToolsetRegistry()
        tool = registry.get("hunter.request", credentials=HunterCredentials(api_key="hunter-registry-key"))

        self.assertEqual(tool.key, "hunter.request")


if __name__ == "__main__":
    unittest.main()
