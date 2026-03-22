"""Tests for harnessiq.providers.paperclip."""

from __future__ import annotations

import unittest

from harnessiq.providers.paperclip import (
    DEFAULT_BASE_URL,
    PaperclipClient,
    PaperclipCredentials,
    build_headers,
    build_paperclip_operation_catalog,
    get_paperclip_operation,
)
from harnessiq.shared.tools import PAPERCLIP_REQUEST
from harnessiq.tools.paperclip import create_paperclip_tools
from harnessiq.tools.registry import ToolRegistry


class PaperclipCredentialsTests(unittest.TestCase):
    def test_valid_credentials_accepted(self) -> None:
        credentials = PaperclipCredentials(api_key="pc_test_token")
        self.assertEqual(credentials.api_key, "pc_test_token")

    def test_blank_api_key_raises(self) -> None:
        with self.assertRaises(ValueError):
            PaperclipCredentials(api_key="")

    def test_blank_api_key_whitespace_raises(self) -> None:
        with self.assertRaises(ValueError):
            PaperclipCredentials(api_key="   ")

    def test_zero_timeout_raises(self) -> None:
        with self.assertRaises(ValueError):
            PaperclipCredentials(api_key="pc_test_token", timeout_seconds=0)

    def test_default_base_url_set(self) -> None:
        credentials = PaperclipCredentials(api_key="pc_test_token")
        self.assertEqual(credentials.base_url, DEFAULT_BASE_URL)

    def test_as_redacted_dict_excludes_raw_key(self) -> None:
        summary = PaperclipCredentials(api_key="pc_super_secret").as_redacted_dict()
        self.assertNotIn("pc_super_secret", str(summary))
        self.assertIn("api_key_masked", summary)


class PaperclipApiTests(unittest.TestCase):
    def test_build_headers_produces_bearer_auth_header(self) -> None:
        headers = build_headers("pc_test_token")
        self.assertEqual(headers["Authorization"], "Bearer pc_test_token")
        self.assertNotIn("X-Paperclip-Run-Id", headers)

    def test_build_headers_includes_run_id_when_provided(self) -> None:
        headers = build_headers("pc_test_token", run_id="run-123")
        self.assertEqual(headers["X-Paperclip-Run-Id"], "run-123")


class PaperclipOperationCatalogTests(unittest.TestCase):
    def test_catalog_is_non_empty(self) -> None:
        catalog = build_paperclip_operation_catalog()
        self.assertGreater(len(catalog), 0)

    def test_catalog_covers_expected_categories(self) -> None:
        categories = {operation.category for operation in build_paperclip_operation_catalog()}
        self.assertEqual(categories, {"Companies", "Agents", "Issues", "Approvals", "Activity", "Costs"})

    def test_representative_issue_operation_requires_payload(self) -> None:
        operation = get_paperclip_operation("checkout_issue")
        self.assertTrue(operation.payload_required)
        self.assertTrue(operation.supports_run_id)

    def test_list_issues_allows_query(self) -> None:
        operation = get_paperclip_operation("list_issues")
        self.assertTrue(operation.allow_query)

    def test_get_operation_raises_for_unknown(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            get_paperclip_operation("nonexistent_op")
        self.assertIn("nonexistent_op", str(ctx.exception))


class PaperclipClientTests(unittest.TestCase):
    def _client(self, request_executor=None) -> PaperclipClient:
        credentials = PaperclipCredentials(api_key="pc_test_token")
        return PaperclipClient(credentials=credentials, request_executor=request_executor or (lambda method, url, **kwargs: {"ok": True}))

    def test_prepare_request_renders_issue_list_url_and_query(self) -> None:
        prepared = self._client().prepare_request(
            "list_issues",
            path_params={"company_id": "company-1"},
            query={"status": "todo,in_progress", "assigneeAgentId": "agent-42"},
        )
        self.assertEqual(prepared.method, "GET")
        self.assertIn("/companies/company-1/issues", prepared.url)
        self.assertIn("status=todo%2Cin_progress", prepared.url)
        self.assertIn("assigneeAgentId=agent-42", prepared.url)

    def test_prepare_request_sets_run_id_header_on_mutation(self) -> None:
        prepared = self._client().prepare_request(
            "update_issue",
            path_params={"issue_id": "issue-1"},
            payload={"status": "done", "comment": "Finished."},
            run_id="run-123",
        )
        self.assertEqual(prepared.headers["Authorization"], "Bearer pc_test_token")
        self.assertEqual(prepared.headers["X-Paperclip-Run-Id"], "run-123")
        self.assertEqual(prepared.json_body["status"], "done")

    def test_prepare_request_ignores_run_id_for_read_operation(self) -> None:
        prepared = self._client().prepare_request("get_issue", path_params={"issue_id": "issue-1"}, run_id="run-123")
        self.assertNotIn("X-Paperclip-Run-Id", prepared.headers)

    def test_prepare_request_raises_on_missing_path_param(self) -> None:
        with self.assertRaises(ValueError):
            self._client().prepare_request("get_company")

    def test_prepare_request_raises_on_query_for_non_query_operation(self) -> None:
        with self.assertRaises(ValueError):
            self._client().prepare_request("get_issue", path_params={"issue_id": "issue-1"}, query={"status": "todo"})

    def test_prepare_request_raises_on_missing_required_payload(self) -> None:
        with self.assertRaises(ValueError):
            self._client().prepare_request("create_issue", path_params={"company_id": "company-1"})

    def test_prepare_request_rejects_payload_for_payloadless_operation(self) -> None:
        with self.assertRaises(ValueError):
            self._client().prepare_request("list_companies", payload={"unexpected": True})

    def test_execute_operation_delegates_to_request_executor(self) -> None:
        captured: list[dict[str, object]] = []

        def fake_request(method: str, url: str, **kwargs: object) -> dict[str, object]:
            captured.append({"method": method, "url": url, **kwargs})
            return {"id": "company-1"}

        result = self._client(request_executor=fake_request).execute_operation("list_companies")
        self.assertEqual(result["id"], "company-1")
        self.assertEqual(captured[0]["method"], "GET")
        self.assertIn("/companies", captured[0]["url"])


class PaperclipToolsTests(unittest.TestCase):
    def test_create_paperclip_tools_returns_registerable_tuple(self) -> None:
        credentials = PaperclipCredentials(api_key="pc_test_token")
        tools = create_paperclip_tools(credentials=credentials)
        self.assertEqual(len(tools), 1)
        ToolRegistry(tools)

    def test_tool_definition_key_is_paperclip_request(self) -> None:
        credentials = PaperclipCredentials(api_key="pc_test_token")
        tools = create_paperclip_tools(credentials=credentials)
        self.assertEqual(tools[0].definition.key, PAPERCLIP_REQUEST)

    def test_tool_handler_executes_operation(self) -> None:
        captured: list[dict[str, object]] = []

        def fake_request(method: str, url: str, **kwargs: object) -> dict[str, object]:
            captured.append({"method": method, "url": url, **kwargs})
            return {"id": "issue-1", "status": "done"}

        client = PaperclipClient(credentials=PaperclipCredentials(api_key="pc_test_token"), request_executor=fake_request)
        registry = ToolRegistry(create_paperclip_tools(client=client))

        result = registry.execute(
            PAPERCLIP_REQUEST,
            {
                "operation": "update_issue",
                "path_params": {"issue_id": "issue-1"},
                "payload": {"status": "done", "comment": "Finished."},
                "run_id": "run-123",
            },
        )

        self.assertEqual(result.output["operation"], "update_issue")
        self.assertEqual(captured[0]["headers"]["X-Paperclip-Run-Id"], "run-123")
        self.assertEqual(captured[0]["json_body"]["status"], "done")

    def test_create_paperclip_tools_raises_without_credentials_or_client(self) -> None:
        with self.assertRaises(ValueError):
            create_paperclip_tools()

    def test_allowed_operations_subset(self) -> None:
        credentials = PaperclipCredentials(api_key="pc_test_token")
        tools = create_paperclip_tools(credentials=credentials, allowed_operations=["get_current_agent", "list_issues"])
        enum_values = tools[0].definition.input_schema["properties"]["operation"]["enum"]
        self.assertEqual(set(enum_values), {"get_current_agent", "list_issues"})


if __name__ == "__main__":
    unittest.main()
