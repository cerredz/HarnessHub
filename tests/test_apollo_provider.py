"""Unit tests for the Apollo.io provider."""

from __future__ import annotations

import unittest

from harnessiq.providers.apollo.api import DEFAULT_BASE_URL, build_headers
from harnessiq.providers.apollo.client import ApolloClient, ApolloCredentials
from harnessiq.providers.apollo.operations import (
    build_apollo_operation_catalog,
    build_apollo_request_tool_definition,
    create_apollo_tools,
    get_apollo_operation,
)


def _mock_executor(response: object):
    def executor(method, url, *, headers, json_body, timeout_seconds):
        return response
    return executor


class ApolloCredentialsTests(unittest.TestCase):
    def test_valid_credentials(self):
        creds = ApolloCredentials(api_key="test-key-123")
        self.assertEqual(creds.api_key, "test-key-123")
        self.assertEqual(creds.base_url, DEFAULT_BASE_URL)
        self.assertEqual(creds.timeout_seconds, 60.0)

    def test_blank_api_key_raises(self):
        with self.assertRaises(ValueError, msg="api_key must not be blank"):
            ApolloCredentials(api_key="")

    def test_whitespace_api_key_raises(self):
        with self.assertRaises(ValueError):
            ApolloCredentials(api_key="   ")

    def test_blank_base_url_raises(self):
        with self.assertRaises(ValueError):
            ApolloCredentials(api_key="key", base_url="")

    def test_zero_timeout_raises(self):
        with self.assertRaises(ValueError):
            ApolloCredentials(api_key="key", timeout_seconds=0)

    def test_negative_timeout_raises(self):
        with self.assertRaises(ValueError):
            ApolloCredentials(api_key="key", timeout_seconds=-1)

    def test_masked_api_key_short(self):
        creds = ApolloCredentials(api_key="ab")
        self.assertEqual(creds.masked_api_key(), "**")

    def test_masked_api_key_long(self):
        creds = ApolloCredentials(api_key="abcdefghijklmn")
        masked = creds.masked_api_key()
        self.assertTrue(masked.startswith("abc"))
        self.assertTrue(masked.endswith("lmn"))
        self.assertNotIn("defghijk", masked)

    def test_as_redacted_dict_no_raw_key(self):
        creds = ApolloCredentials(api_key="super-secret-key")
        d = creds.as_redacted_dict()
        self.assertNotIn("super-secret-key", str(d))
        self.assertIn("api_key_masked", d)
        self.assertIn("base_url", d)
        self.assertIn("timeout_seconds", d)


class ApolloApiTests(unittest.TestCase):
    def test_build_headers_contains_auth(self):
        headers = build_headers("my-api-key")
        self.assertEqual(headers["X-Api-Key"], "my-api-key")

    def test_build_headers_contains_content_type(self):
        headers = build_headers("key")
        self.assertEqual(headers["Content-Type"], "application/json")

    def test_build_headers_extra(self):
        headers = build_headers("key", extra_headers={"X-Custom": "value"})
        self.assertEqual(headers["X-Custom"], "value")


class ApolloOperationCatalogTests(unittest.TestCase):
    def test_catalog_returns_all_operations(self):
        catalog = build_apollo_operation_catalog()
        self.assertEqual(len(catalog), 25)

    def test_catalog_operation_names(self):
        catalog = build_apollo_operation_catalog()
        names = {op.name for op in catalog}
        self.assertIn("search_people", names)
        self.assertIn("enrich_person", names)
        self.assertIn("bulk_enrich_people", names)
        self.assertIn("search_contacts", names)
        self.assertIn("create_contact", names)
        self.assertIn("update_contact", names)
        self.assertIn("search_organizations", names)
        self.assertIn("enrich_organization", names)
        self.assertIn("search_accounts", names)
        self.assertIn("bulk_create_accounts", names)
        self.assertIn("update_account", names)
        self.assertIn("search_sequences", names)
        self.assertIn("add_contacts_to_sequence", names)
        self.assertIn("remove_contacts_from_sequence", names)
        self.assertIn("list_email_accounts", names)
        self.assertIn("search_deals", names)
        self.assertIn("create_deal", names)
        self.assertIn("update_deal", names)
        self.assertIn("search_tasks", names)
        self.assertIn("bulk_create_tasks", names)
        self.assertIn("search_calls", names)
        self.assertIn("create_call", names)
        self.assertIn("update_call", names)
        self.assertIn("list_users", names)
        self.assertIn("get_api_usage", names)

    def test_get_operation_valid(self):
        op = get_apollo_operation("search_people")
        self.assertEqual(op.name, "search_people")
        self.assertEqual(op.method, "POST")

    def test_get_operation_invalid_raises(self):
        with self.assertRaises(ValueError) as ctx:
            get_apollo_operation("nonexistent_op")
        self.assertIn("nonexistent_op", str(ctx.exception))
        self.assertIn("Available:", str(ctx.exception))

    def test_path_params_on_update_contact(self):
        op = get_apollo_operation("update_contact")
        self.assertIn("contact_id", op.required_path_params)

    def test_path_params_on_update_account(self):
        op = get_apollo_operation("update_account")
        self.assertIn("account_id", op.required_path_params)

    def test_path_params_on_add_contacts_to_sequence(self):
        op = get_apollo_operation("add_contacts_to_sequence")
        self.assertIn("sequence_id", op.required_path_params)

    def test_enrich_organization_uses_get(self):
        op = get_apollo_operation("enrich_organization")
        self.assertEqual(op.method, "GET")
        self.assertTrue(op.allow_query)


class ApolloClientTests(unittest.TestCase):
    def _make_client(self, response=None):
        creds = ApolloCredentials(api_key="test-apollo-key")
        return ApolloClient(
            credentials=creds,
            request_executor=_mock_executor(response or {"results": []}),
        )

    def test_prepare_request_search_people(self):
        client = self._make_client()
        prepared = client.prepare_request(
            "search_people", payload={"person_titles": ["Engineer"]}
        )
        self.assertEqual(prepared.method, "POST")
        self.assertIn("/mixed_people/api_search", prepared.url)
        self.assertEqual(prepared.headers["X-Api-Key"], "test-apollo-key")
        self.assertEqual(prepared.json_body, {"person_titles": ["Engineer"]})

    def test_prepare_request_missing_path_param_raises(self):
        client = self._make_client()
        with self.assertRaises(ValueError) as ctx:
            client.prepare_request("update_contact", payload={"first_name": "John"})
        self.assertIn("contact_id", str(ctx.exception))

    def test_prepare_request_payload_to_no_payload_op_raises(self):
        client = self._make_client()
        with self.assertRaises(ValueError) as ctx:
            client.prepare_request("list_email_accounts", payload={"foo": "bar"})
        self.assertIn("does not accept a payload", str(ctx.exception))

    def test_prepare_request_missing_required_payload_raises(self):
        client = self._make_client()
        with self.assertRaises(ValueError) as ctx:
            client.prepare_request("search_people")
        self.assertIn("requires a payload", str(ctx.exception))

    def test_prepare_request_path_param_substituted(self):
        client = self._make_client()
        prepared = client.prepare_request(
            "update_contact",
            path_params={"contact_id": "abc-123"},
            payload={"first_name": "Jane"},
        )
        self.assertIn("abc-123", prepared.url)
        self.assertNotIn("{contact_id}", prepared.url)

    def test_execute_operation_returns_response(self):
        client = self._make_client(response={"people": []})
        result = client.execute_operation("search_people", payload={"q": "engineer"})
        self.assertEqual(result, {"people": []})

    def test_prepare_request_query_params_included(self):
        client = self._make_client()
        prepared = client.prepare_request(
            "enrich_organization", query={"domain": "acme.com"}
        )
        self.assertIn("acme.com", prepared.url)


class ApolloToolTests(unittest.TestCase):
    def _make_creds(self):
        return ApolloCredentials(api_key="apollo-tool-key")

    def test_create_apollo_tools_returns_one_tool(self):
        tools = create_apollo_tools(credentials=self._make_creds())
        self.assertEqual(len(tools), 1)

    def test_tool_key_is_correct(self):
        tools = create_apollo_tools(credentials=self._make_creds())
        self.assertEqual(tools[0].key, "apollo.request")

    def test_tool_name_is_correct(self):
        tools = create_apollo_tools(credentials=self._make_creds())
        self.assertEqual(tools[0].definition.name, "apollo_request")

    def test_create_apollo_tools_no_credentials_raises(self):
        with self.assertRaises(ValueError):
            create_apollo_tools()

    def test_allowed_operations_filters_catalog(self):
        tools = create_apollo_tools(
            credentials=self._make_creds(),
            allowed_operations=["enrich_person"],
        )
        schema = tools[0].definition.input_schema
        self.assertEqual(schema["properties"]["operation"]["enum"], ["enrich_person"])

    def test_tool_definition_has_required_operation_field(self):
        definition = build_apollo_request_tool_definition()
        self.assertIn("operation", definition.input_schema["required"])

    def test_handler_returns_expected_shape(self):
        response = {"people": [{"name": "Alice"}]}
        creds = self._make_creds()
        client = ApolloClient(
            credentials=creds,
            request_executor=_mock_executor(response),
        )
        tools = create_apollo_tools(client=client)
        result = tools[0].handler({"operation": "search_people", "payload": {"q": "alice"}})
        self.assertIn("operation", result)
        self.assertIn("method", result)
        self.assertIn("path", result)
        self.assertIn("response", result)
        self.assertEqual(result["response"], response)

    def test_handler_invalid_operation_raises(self):
        tools = create_apollo_tools(credentials=self._make_creds())
        with self.assertRaises(ValueError):
            tools[0].handler({"operation": "invalid_op"})


if __name__ == "__main__":
    unittest.main()
