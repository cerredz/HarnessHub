"""Tests for the Resend tooling surface."""

from __future__ import annotations

import unittest

from harnessiq.shared.resend import (
    ResendCredentials as SharedResendCredentials,
    build_resend_operation_catalog as shared_build_resend_operation_catalog,
)
from harnessiq.tools import RESEND_REQUEST, ResendClient, ResendCredentials, build_resend_operation_catalog, create_resend_tools
from harnessiq.tools.registry import ToolRegistry


class ResendToolsTests(unittest.TestCase):
    def test_shared_resend_facade_preserves_public_models_and_catalog(self) -> None:
        self.assertIs(ResendCredentials, SharedResendCredentials)
        self.assertEqual(SharedResendCredentials.__module__, "harnessiq.shared.resend")
        self.assertEqual(len(shared_build_resend_operation_catalog()), 64)

    def test_operation_catalog_covers_expected_resend_surface(self) -> None:
        catalog = build_resend_operation_catalog()
        names = {operation.name for operation in catalog}

        self.assertEqual(len(catalog), 64)
        self.assertIn("send_email", names)
        self.assertIn("send_batch_emails", names)
        self.assertIn("create_contact_property", names)
        self.assertIn("publish_template", names)
        self.assertIn("delete_webhook", names)
        self.assertIn("create_audience", names)

    def test_resend_request_tool_executes_send_email_with_idempotency_key(self) -> None:
        captured: dict[str, object] = {}

        def fake_request_executor(method: str, url: str, **kwargs: object) -> dict[str, object]:
            captured["method"] = method
            captured["url"] = url
            captured["kwargs"] = kwargs
            return {"id": "email_123"}

        registry = ToolRegistry(
            create_resend_tools(
                client=ResendClient(
                    credentials=ResendCredentials(api_key="re_test_1234567890"),
                    request_executor=fake_request_executor,
                )
            )
        )

        result = registry.execute(
            RESEND_REQUEST,
            {
                "operation": "send_email",
                "payload": {
                    "from": "HarnessHub <hello@example.com>",
                    "to": ["user@example.com"],
                    "subject": "Welcome",
                    "html": "<p>Hello</p>",
                },
                "idempotency_key": "idem_123",
            },
        )

        self.assertEqual(result.output["operation"], "send_email")
        self.assertEqual(result.output["response"], {"id": "email_123"})
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["url"], "https://api.resend.com/emails")
        self.assertEqual(captured["kwargs"]["headers"]["Authorization"], "Bearer re_test_1234567890")
        self.assertEqual(captured["kwargs"]["headers"]["Idempotency-Key"], "idem_123")
        self.assertEqual(captured["kwargs"]["json_body"]["subject"], "Welcome")

    def test_resend_request_tool_supports_batch_validation_headers(self) -> None:
        captured: dict[str, object] = {}

        def fake_request_executor(method: str, url: str, **kwargs: object) -> dict[str, object]:
            captured["method"] = method
            captured["url"] = url
            captured["kwargs"] = kwargs
            return {"data": [{"id": "email_1"}]}

        registry = ToolRegistry(
            create_resend_tools(
                client=ResendClient(
                    credentials=ResendCredentials(api_key="re_test_1234567890"),
                    request_executor=fake_request_executor,
                )
            )
        )

        result = registry.execute(
            RESEND_REQUEST,
            {
                "operation": "send_batch_emails",
                "payload": [
                    {
                        "from": "HarnessHub <hello@example.com>",
                        "to": ["user@example.com"],
                        "subject": "Welcome",
                        "html": "<p>Hello</p>",
                    }
                ],
                "batch_validation": "permissive",
            },
        )

        self.assertEqual(result.output["response"]["data"][0]["id"], "email_1")
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["url"], "https://api.resend.com/emails/batch")
        self.assertEqual(captured["kwargs"]["headers"]["x-batch-validation"], "permissive")

    def test_resend_request_tool_builds_dynamic_contact_paths_and_query_strings(self) -> None:
        captured: dict[str, object] = {}

        def fake_request_executor(method: str, url: str, **kwargs: object) -> dict[str, object]:
            captured["method"] = method
            captured["url"] = url
            captured["kwargs"] = kwargs
            return {"data": []}

        registry = ToolRegistry(
            create_resend_tools(
                client=ResendClient(
                    credentials=ResendCredentials(api_key="re_test_1234567890"),
                    request_executor=fake_request_executor,
                )
            )
        )

        registry.execute(
            RESEND_REQUEST,
            {
                "operation": "list_contacts",
                "path_params": {"audience_id": "aud_123"},
                "query": {"limit": 25, "after": "cursor_1"},
            },
        )

        self.assertEqual(captured["method"], "GET")
        self.assertEqual(
            captured["url"],
            "https://api.resend.com/audiences/aud_123/contacts?limit=25&after=cursor_1",
        )
        self.assertIsNone(captured["kwargs"]["json_body"])

    def test_resend_request_tool_rejects_invalid_operation_arguments(self) -> None:
        client = ResendClient(credentials=ResendCredentials(api_key="re_test_1234567890"), request_executor=lambda *args, **kwargs: {})

        with self.assertRaisesRegex(ValueError, "requires a payload"):
            client.prepare_request("send_email")

        with self.assertRaisesRegex(ValueError, "does not support batch_validation"):
            client.prepare_request(
                "send_email",
                payload={"to": ["user@example.com"]},
                batch_validation="strict",
            )


if __name__ == "__main__":
    unittest.main()
