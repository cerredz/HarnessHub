"""Tests for harnessiq.providers.browser_use."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from harnessiq.providers.browser_use.client import BrowserUseClient
from harnessiq.providers.browser_use.operations import (
    BrowserUseOperation,
    build_browser_use_operation_catalog,
    get_browser_use_operation,
)
from harnessiq.shared.dtos import ProviderPayloadRequestDTO
from harnessiq.shared.http import ProviderHTTPError
from harnessiq.shared.tools import BROWSER_USE_REQUEST
from harnessiq.tools.browser_use import create_browser_use_tools
from harnessiq.tools.registry import ToolRegistry


class BrowserUseOperationCatalogTests(unittest.TestCase):
    def test_catalog_is_non_empty(self) -> None:
        catalog = build_browser_use_operation_catalog()
        self.assertGreater(len(catalog), 0)

    def test_catalog_covers_core_categories(self) -> None:
        catalog = build_browser_use_operation_catalog()
        categories = {operation.category for operation in catalog}
        self.assertIn("Task", categories)
        self.assertIn("Session", categories)
        self.assertIn("Profile", categories)
        self.assertIn("Browser", categories)
        self.assertIn("Skill", categories)
        self.assertIn("Marketplace", categories)

    def test_get_operation_returns_expected_metadata(self) -> None:
        operation = get_browser_use_operation("create_task")
        self.assertIsInstance(operation, BrowserUseOperation)
        self.assertEqual(operation.category, "Task")

    def test_get_operation_raises_for_unknown(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            get_browser_use_operation("not_real")
        self.assertIn("not_real", str(ctx.exception))


class BrowserUseClientTests(unittest.TestCase):
    def test_create_task_uses_browser_use_headers_and_payload(self) -> None:
        captured: dict[str, object] = {}

        def fake(method, url, **kwargs):  # noqa: ANN001
            captured["method"] = method
            captured["url"] = url
            captured["headers"] = kwargs.get("headers")
            captured["json_body"] = kwargs.get("json_body")
            return {"id": "task_123"}

        client = BrowserUseClient(api_key="bu_test_key", request_executor=fake)
        result = client.create_task(
            "Open example.com and summarize it",
            session_id="session_123",
            max_steps=7,
            allowed_domains=["example.com"],
            metadata={"source": "test"},
        )

        self.assertEqual(result["id"], "task_123")
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["url"], "https://api.browser-use.com/api/v2/tasks")
        self.assertEqual(captured["headers"]["X-Browser-Use-API-Key"], "bu_test_key")
        self.assertEqual(
            captured["json_body"],
            {
                "task": "Open example.com and summarize it",
                "sessionId": "session_123",
                "maxSteps": 7,
                "allowedDomains": ["example.com"],
                "metadata": {"source": "test"},
            },
        )

    def test_list_tasks_encodes_query_params(self) -> None:
        captured: dict[str, object] = {}

        def fake(method, url, **kwargs):  # noqa: ANN001
            captured["method"] = method
            captured["url"] = url
            return {"items": []}

        client = BrowserUseClient(api_key="bu_test_key", request_executor=fake)
        client.list_tasks(page_size=25, page_number=2, filter_by="finished")

        self.assertEqual(captured["method"], "GET")
        self.assertIn("pageSize=25", captured["url"])
        self.assertIn("pageNumber=2", captured["url"])
        self.assertIn("filterBy=finished", captured["url"])

    def test_request_retries_on_rate_limit(self) -> None:
        attempts = {"count": 0}

        def fake(method, url, **kwargs):  # noqa: ANN001
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise ProviderHTTPError(
                    provider="browser_use",
                    message="Too many requests",
                    status_code=429,
                    url=url,
                )
            return {"status": "ok"}

        client = BrowserUseClient(api_key="bu_test_key", request_executor=fake, max_retries=1)
        with patch("harnessiq.providers.browser_use.client.time.sleep") as sleep:
            result = client.get_task("task_123")

        self.assertEqual(result, {"status": "ok"})
        self.assertEqual(attempts["count"], 2)
        sleep.assert_called_once()

    def test_execute_operation_accepts_payload_request_dto(self) -> None:
        client = BrowserUseClient(
            api_key="bu_test_key",
            request_executor=lambda method, url, **kwargs: {"method": method, "url": url, "kwargs": kwargs},
        )

        result = client.execute_operation(
            ProviderPayloadRequestDTO(
                operation="get_task_status",
                payload={"task_id": "task_123"},
            )
        )

        self.assertEqual(result.operation, "get_task_status")
        self.assertIn("/tasks/task_123/status", result.result["url"])


class BrowserUseToolsTests(unittest.TestCase):
    def _client(self) -> BrowserUseClient:
        return BrowserUseClient(
            api_key="bu_test_key",
            request_executor=lambda method, url, **kwargs: {"method": method, "url": url, "kwargs": kwargs},
        )

    def test_create_browser_use_tools_returns_registerable_tuple(self) -> None:
        tools = create_browser_use_tools(client=self._client())
        self.assertEqual(len(tools), 1)
        ToolRegistry(tools)

    def test_tool_definition_key_is_browser_use_request(self) -> None:
        tools = create_browser_use_tools(client=self._client())
        self.assertEqual(tools[0].definition.key, BROWSER_USE_REQUEST)

    def test_tool_handler_executes_selected_operation(self) -> None:
        tools = create_browser_use_tools(client=self._client())
        registry = ToolRegistry(tools)
        result = registry.execute(
            BROWSER_USE_REQUEST,
            {
                "operation": "get_task_status",
                "payload": {"task_id": "task_123"},
            },
        )
        self.assertEqual(result.output["operation"], "get_task_status")
        self.assertIn("/tasks/task_123/status", result.output["result"]["url"])

    def test_create_browser_use_tools_raises_without_credentials_or_client(self) -> None:
        with self.assertRaises(ValueError):
            create_browser_use_tools()

    def test_allowed_operations_subset(self) -> None:
        tools = create_browser_use_tools(
            client=self._client(),
            allowed_operations=["create_task", "get_task_status"],
        )
        enum_values = tools[0].definition.input_schema["properties"]["operation"]["enum"]
        self.assertEqual(set(enum_values), {"create_task", "get_task_status"})


if __name__ == "__main__":
    unittest.main()
