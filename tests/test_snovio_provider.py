"""Tests for the Snov.io provider client and request builders."""

from __future__ import annotations

import unittest
from unittest.mock import Mock
from urllib import parse

from harnessiq.providers.snovio import (
    SnovioClient,
    SnovioCredentials,
    build_access_token_request,
    build_add_prospect_request,
    build_add_to_campaign_request,
    build_campaign_data_params,
    build_campaign_recipients_params,
    build_delete_from_list_request,
    build_delete_prospect_request,
    build_domain_search_params,
    build_email_info_request,
    build_email_verifier_request,
    build_emails_count_params,
    build_emails_from_names_request,
    build_get_list_params,
    build_get_prospect_params,
    build_pause_campaign_request,
    build_profile_emails_request,
    build_start_campaign_request,
    build_update_prospect_request,
    build_url_search_request,
    build_user_info_params,
)
from harnessiq.shared.dtos import ProviderPayloadRequestDTO, ProviderPayloadResultDTO


class SnovioCredentialsTests(unittest.TestCase):
    def test_credentials_type_holds_required_fields(self) -> None:
        creds = SnovioCredentials(client_id="cid", client_secret="csecret")
        self.assertEqual(creds["client_id"], "cid")
        self.assertEqual(creds["client_secret"], "csecret")


class SnovioRequestBuilderTests(unittest.TestCase):
    def test_build_access_token_request_returns_urlencoded_body(self) -> None:
        body = build_access_token_request("my_client_id", "my_client_secret")
        params = dict(parse.parse_qsl(body))
        self.assertEqual(params["grant_type"], "client_credentials")
        self.assertEqual(params["client_id"], "my_client_id")
        self.assertEqual(params["client_secret"], "my_client_secret")

    def test_build_domain_search_params_includes_required_fields(self) -> None:
        params = build_domain_search_params("tok", "example.com")
        self.assertEqual(params["access_token"], "tok")
        self.assertEqual(params["domain"], "example.com")
        self.assertNotIn("type", params)
        self.assertNotIn("limit", params)

    def test_build_domain_search_params_includes_optional_fields(self) -> None:
        params = build_domain_search_params("tok", "example.com", type="personal", limit=25, last_id=42)
        self.assertEqual(params["type"], "personal")
        self.assertEqual(params["limit"], 25)
        self.assertEqual(params["lastId"], 42)

    def test_build_emails_count_params_omits_none_type(self) -> None:
        params = build_emails_count_params("tok", "example.com")
        self.assertNotIn("type", params)

    def test_build_emails_from_names_request_returns_correct_keys(self) -> None:
        body = build_emails_from_names_request("tok", "Alice", "Smith", "example.com")
        self.assertEqual(body["firstName"], "Alice")
        self.assertEqual(body["lastName"], "Smith")
        self.assertEqual(body["domain"], "example.com")
        self.assertEqual(body["access_token"], "tok")

    def test_build_email_verifier_request(self) -> None:
        body = build_email_verifier_request("tok", "alice@example.com")
        self.assertEqual(body["email"], "alice@example.com")
        self.assertEqual(body["access_token"], "tok")

    def test_build_email_info_request(self) -> None:
        body = build_email_info_request("tok", "alice@example.com")
        self.assertEqual(body["email"], "alice@example.com")

    def test_build_profile_emails_request(self) -> None:
        body = build_profile_emails_request("tok", "https://linkedin.com/in/alice")
        self.assertEqual(body["url"], "https://linkedin.com/in/alice")

    def test_build_url_search_request(self) -> None:
        body = build_url_search_request("tok", "https://linkedin.com/in/alice")
        self.assertEqual(body["url"], "https://linkedin.com/in/alice")

    def test_build_get_prospect_params(self) -> None:
        params = build_get_prospect_params("tok", "p_123")
        self.assertEqual(params["id"], "p_123")

    def test_build_add_prospect_request_required_fields(self) -> None:
        body = build_add_prospect_request("tok", "a@b.com", "Alice Smith", "list_1")
        self.assertEqual(body["email"], "a@b.com")
        self.assertEqual(body["fullName"], "Alice Smith")
        self.assertEqual(body["listId"], "list_1")

    def test_build_add_prospect_request_optional_fields_omitted_when_none(self) -> None:
        body = build_add_prospect_request("tok", "a@b.com", "Alice Smith", "list_1")
        self.assertNotIn("firstName", body)
        self.assertNotIn("companyName", body)
        self.assertNotIn("linkedInUrl", body)

    def test_build_add_prospect_request_includes_optional_fields(self) -> None:
        body = build_add_prospect_request(
            "tok", "a@b.com", "Alice Smith", "list_1",
            first_name="Alice", company_name="Acme", linkedin_url="https://li.com/in/alice"
        )
        self.assertEqual(body["firstName"], "Alice")
        self.assertEqual(body["companyName"], "Acme")
        self.assertEqual(body["linkedInUrl"], "https://li.com/in/alice")

    def test_build_update_prospect_request_merges_fields(self) -> None:
        body = build_update_prospect_request("tok", "p_1", {"companyName": "NewCo"})
        self.assertEqual(body["id"], "p_1")
        self.assertEqual(body["companyName"], "NewCo")

    def test_build_delete_prospect_request(self) -> None:
        body = build_delete_prospect_request("tok", "p_1")
        self.assertEqual(body["id"], "p_1")

    def test_build_get_list_params(self) -> None:
        params = build_get_list_params("tok", "list_5")
        self.assertEqual(params["listId"], "list_5")

    def test_build_delete_from_list_request(self) -> None:
        body = build_delete_from_list_request("tok", "list_5", "a@b.com")
        self.assertEqual(body["listId"], "list_5")
        self.assertEqual(body["email"], "a@b.com")

    def test_build_campaign_data_params(self) -> None:
        params = build_campaign_data_params("tok", "camp_1")
        self.assertEqual(params["id"], "camp_1")

    def test_build_campaign_recipients_params_omits_none_status(self) -> None:
        params = build_campaign_recipients_params("tok", "camp_1")
        self.assertNotIn("status", params)
        self.assertEqual(params["id"], "camp_1")

    def test_build_campaign_recipients_params_includes_status(self) -> None:
        params = build_campaign_recipients_params("tok", "camp_1", status="opened")
        self.assertEqual(params["status"], "opened")

    def test_build_add_to_campaign_request(self) -> None:
        body = build_add_to_campaign_request("tok", "camp_1", ["a@b.com", "c@d.com"])
        self.assertEqual(body["id"], "camp_1")
        self.assertEqual(body["emails"], ["a@b.com", "c@d.com"])

    def test_build_start_campaign_request(self) -> None:
        body = build_start_campaign_request("tok", "camp_1")
        self.assertEqual(body["id"], "camp_1")

    def test_build_pause_campaign_request(self) -> None:
        body = build_pause_campaign_request("tok", "camp_1")
        self.assertEqual(body["id"], "camp_1")

    def test_build_user_info_params(self) -> None:
        params = build_user_info_params("tok")
        self.assertEqual(params["access_token"], "tok")

    def test_request_builders_produce_no_mutations(self) -> None:
        custom = {"extra_field": "val"}
        build_update_prospect_request("tok", "p_1", custom)
        self.assertEqual(custom, {"extra_field": "val"})


class SnovioClientTests(unittest.TestCase):
    def _make_client(self, captured: list[dict]) -> SnovioClient:
        def fake_executor(method, url, *, headers=None, json_body=None, timeout_seconds=60.0):
            captured.append({"method": method, "url": url, "json_body": json_body, "headers": headers})
            return {"status": "ok"}

        return SnovioClient(
            client_id="cid",
            client_secret="csecret",
            request_executor=fake_executor,
        )

    def test_client_is_frozen_dataclass(self) -> None:
        client = SnovioClient(client_id="cid", client_secret="csecret")
        with self.assertRaises(Exception):
            client.client_id = "modified"  # type: ignore[misc]

    def test_domain_search_calls_correct_url_and_method(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.domain_search("tok", "example.com")
        self.assertEqual(captured[0]["method"], "GET")
        self.assertIn("get-domain-search", captured[0]["url"])
        self.assertIn("domain=example.com", captured[0]["url"])

    def test_verify_email_calls_post(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.verify_email("tok", "a@b.com")
        self.assertEqual(captured[0]["method"], "POST")
        self.assertIn("email-verifier", captured[0]["url"])
        self.assertEqual(captured[0]["json_body"]["email"], "a@b.com")

    def test_add_prospect_calls_post_with_correct_body(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.add_prospect("tok", "a@b.com", "Alice Smith", "list_1")
        self.assertEqual(captured[0]["method"], "POST")
        self.assertEqual(captured[0]["json_body"]["email"], "a@b.com")

    def test_start_campaign_calls_post(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.start_campaign("tok", "camp_1")
        self.assertEqual(captured[0]["method"], "POST")
        self.assertIn("start-campaign", captured[0]["url"])

    def test_delete_prospect_calls_delete(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.delete_prospect("tok", "p_1")
        self.assertEqual(captured[0]["method"], "DELETE")
        self.assertIn("delete-prospect", captured[0]["url"])

    def test_get_user_info_calls_v2_me(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.get_user_info("tok")
        self.assertEqual(captured[0]["method"], "GET")
        self.assertIn("/v2/me", captured[0]["url"])

    def test_execute_operation_accepts_payload_request_dto(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)

        result = client.execute_operation(
            ProviderPayloadRequestDTO(operation="get_user_info", payload={"access_token": "tok"})
        )

        self.assertIsInstance(result, ProviderPayloadResultDTO)
        self.assertEqual(result.operation, "get_user_info")


class SnovioOperationCatalogTests(unittest.TestCase):
    def test_catalog_is_non_empty(self) -> None:
        from harnessiq.providers.snovio.operations import build_snovio_operation_catalog
        catalog = build_snovio_operation_catalog()
        self.assertGreater(len(catalog), 0)

    def test_catalog_covers_core_categories(self) -> None:
        from harnessiq.providers.snovio.operations import build_snovio_operation_catalog
        catalog = build_snovio_operation_catalog()
        categories = {op.category for op in catalog}
        self.assertIn("Email Discovery", categories)
        self.assertIn("Prospect", categories)
        self.assertIn("Campaign", categories)
        self.assertIn("Account", categories)

    def test_domain_search_is_in_catalog(self) -> None:
        from harnessiq.providers.snovio.operations import get_snovio_operation
        op = get_snovio_operation("domain_search")
        self.assertEqual(op.category, "Email Discovery")

    def test_get_all_campaigns_is_in_catalog(self) -> None:
        from harnessiq.providers.snovio.operations import get_snovio_operation
        op = get_snovio_operation("get_all_campaigns")
        self.assertEqual(op.category, "Campaign")

    def test_get_operation_raises_for_unknown(self) -> None:
        from harnessiq.providers.snovio.operations import get_snovio_operation
        with self.assertRaises(ValueError) as ctx:
            get_snovio_operation("nonexistent_op")
        self.assertIn("nonexistent_op", str(ctx.exception))


class SnovioToolsTests(unittest.TestCase):
    def _client(self) -> SnovioClient:
        return SnovioClient(
            client_id="cid",
            client_secret="sec",
            request_executor=lambda m, u, **kw: {"access_token": "tok"},
        )

    def test_create_snovio_tools_returns_registerable_tuple(self) -> None:
        from harnessiq.tools.snovio import create_snovio_tools
        from harnessiq.tools.registry import ToolRegistry
        tools = create_snovio_tools(client=self._client())
        self.assertEqual(len(tools), 1)
        ToolRegistry(tools)

    def test_tool_definition_key_is_snovio_request(self) -> None:
        from harnessiq.tools.snovio import create_snovio_tools
        from harnessiq.shared.tools import SNOVIO_REQUEST
        tools = create_snovio_tools(client=self._client())
        self.assertEqual(tools[0].definition.key, SNOVIO_REQUEST)

    def test_tool_handler_executes_get_user_info(self) -> None:
        from harnessiq.tools.snovio import create_snovio_tools
        from harnessiq.shared.tools import SNOVIO_REQUEST
        from harnessiq.tools.registry import ToolRegistry
        captured: list[dict] = []

        def fake(method: str, url: str, **kw: object) -> object:
            captured.append({"method": method, "url": url})
            return {"access_token": "tok"} if "oauth" in url else {"credits": 100}

        client = SnovioClient(client_id="cid", client_secret="sec", request_executor=fake)
        tools = create_snovio_tools(client=client)
        registry = ToolRegistry(tools)
        result = registry.execute(SNOVIO_REQUEST, {"operation": "get_user_info"})
        self.assertEqual(result.output["operation"], "get_user_info")
        self.assertGreaterEqual(len(captured), 2)

    def test_tool_handler_injects_access_token_into_dto_request(self) -> None:
        from harnessiq.tools.snovio import create_snovio_tools
        from harnessiq.shared.tools import SNOVIO_REQUEST
        from harnessiq.tools.registry import ToolRegistry

        client = Mock()
        client.get_access_token.return_value = {"access_token": "tok"}
        client.execute_operation.return_value = ProviderPayloadResultDTO(
            operation="get_user_info",
            result={"credits": 100},
        )

        registry = ToolRegistry(create_snovio_tools(client=client))
        result = registry.execute(SNOVIO_REQUEST, {"operation": "get_user_info"})

        self.assertEqual(result.output["operation"], "get_user_info")
        request = client.execute_operation.call_args.args[0]
        self.assertIsInstance(request, ProviderPayloadRequestDTO)
        self.assertEqual(request.payload["access_token"], "tok")

    def test_create_snovio_tools_raises_without_credentials_or_client(self) -> None:
        from harnessiq.tools.snovio import create_snovio_tools
        with self.assertRaises(ValueError):
            create_snovio_tools()

    def test_allowed_operations_subset(self) -> None:
        from harnessiq.tools.snovio import create_snovio_tools
        tools = create_snovio_tools(
            client=self._client(),
            allowed_operations=["domain_search", "verify_email"],
        )
        enum_vals = tools[0].definition.input_schema["properties"]["operation"]["enum"]
        self.assertEqual(set(enum_vals), {"domain_search", "verify_email"})


if __name__ == "__main__":
    unittest.main()
