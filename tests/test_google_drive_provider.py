"""Tests for harnessiq.providers.google_drive."""

from __future__ import annotations

import unittest
from unittest.mock import Mock

from harnessiq.providers.google_drive import (
    FOLDER_MIME_TYPE,
    JSON_MIME_TYPE,
    GoogleDriveClient,
    GoogleDriveCredentials,
    build_google_drive_operation_catalog,
    get_google_drive_operation,
)
from harnessiq.shared.tools import GOOGLE_DRIVE_REQUEST
from harnessiq.tools.google_drive import create_google_drive_tools
from harnessiq.tools.registry import ToolRegistry


class GoogleDriveCredentialsTests(unittest.TestCase):
    def test_valid_credentials_accepted(self) -> None:
        credentials = GoogleDriveCredentials(client_id="cid", client_secret="secret", refresh_token="refresh")
        self.assertEqual(credentials.client_id, "cid")

    def test_blank_client_id_raises(self) -> None:
        with self.assertRaises(ValueError):
            GoogleDriveCredentials(client_id="", client_secret="secret", refresh_token="refresh")

    def test_blank_client_secret_raises(self) -> None:
        with self.assertRaises(ValueError):
            GoogleDriveCredentials(client_id="cid", client_secret=" ", refresh_token="refresh")

    def test_blank_refresh_token_raises(self) -> None:
        with self.assertRaises(ValueError):
            GoogleDriveCredentials(client_id="cid", client_secret="secret", refresh_token="")

    def test_as_redacted_dict_masks_secret_material(self) -> None:
        summary = GoogleDriveCredentials(
            client_id="cid",
            client_secret="secret",
            refresh_token="refresh-token",
        ).as_redacted_dict()
        self.assertEqual(summary["client_secret_masked"], "***")
        self.assertNotIn("refresh-token", str(summary))


class GoogleDriveOperationCatalogTests(unittest.TestCase):
    def test_catalog_contains_expected_operations(self) -> None:
        names = [operation.name for operation in build_google_drive_operation_catalog()]
        self.assertEqual(
            names,
            [
                "ensure_folder",
                "list_files",
                "find_file",
                "get_file",
                "upsert_json_file",
                "copy_file",
                "move_file",
                "create_shortcut",
                "list_permissions",
                "create_permission",
            ],
        )

    def test_unknown_operation_raises(self) -> None:
        with self.assertRaises(ValueError):
            get_google_drive_operation("nope")


class GoogleDriveClientTests(unittest.TestCase):
    def _make_client(
        self,
        *,
        request_executor=None,
        multipart_request_executor=None,
        token_request_executor=None,
    ) -> GoogleDriveClient:
        credentials = GoogleDriveCredentials(client_id="cid", client_secret="secret", refresh_token="refresh")
        return GoogleDriveClient(
            credentials=credentials,
            request_executor=request_executor or (lambda method, url, **kwargs: {"files": []}),
            multipart_request_executor=multipart_request_executor or (lambda method, url, **kwargs: {"id": "file-1", "name": "job.json"}),
            token_request_executor=token_request_executor or (lambda url, **kwargs: {"access_token": "access-123"}),
        )

    def test_refresh_access_token_uses_token_executor(self) -> None:
        captured: list[dict[str, object]] = []

        def fake_token_executor(url: str, **kwargs: object) -> dict[str, str]:
            captured.append({"url": url, **kwargs})
            return {"access_token": "token-123"}

        token = self._make_client(token_request_executor=fake_token_executor).refresh_access_token()

        self.assertEqual(token, "token-123")
        self.assertEqual(captured[0]["form_fields"]["grant_type"], "refresh_token")

    def test_find_file_returns_first_sorted_match(self) -> None:
        client = self._make_client(
            request_executor=lambda method, url, **kwargs: {
                "files": [
                    {"id": "b", "name": "job.json", "mimeType": JSON_MIME_TYPE},
                    {"id": "a", "name": "job.json", "mimeType": JSON_MIME_TYPE},
                ]
            }
        )

        result = client.find_file(name="job.json")

        self.assertEqual(result["id"], "a")

    def test_list_files_rejects_non_positive_page_size(self) -> None:
        client = self._make_client()

        with self.assertRaises(ValueError):
            client.list_files(page_size=0)

    def test_get_file_returns_metadata_object(self) -> None:
        client = self._make_client(
            request_executor=lambda method, url, **kwargs: {
                "id": "file-1",
                "name": "job.json",
                "mimeType": JSON_MIME_TYPE,
            }
        )

        result = client.get_file("file-1")

        self.assertEqual(result["id"], "file-1")

    def test_ensure_folder_reuses_existing_folder(self) -> None:
        client = self._make_client(
            request_executor=lambda method, url, **kwargs: {
                "files": [{"id": "folder-1", "name": "Applications", "mimeType": FOLDER_MIME_TYPE}]
            }
        )

        result = client.ensure_folder(name="Applications")

        self.assertFalse(result["created"])
        self.assertEqual(result["folder"]["id"], "folder-1")

    def test_ensure_folder_creates_missing_folder(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_request(method: str, url: str, **kwargs: object) -> dict[str, object]:
            calls.append({"method": method, "url": url, **kwargs})
            if method == "GET":
                return {"files": []}
            return {"id": "folder-2", "name": "Applications", "mimeType": FOLDER_MIME_TYPE}

        result = self._make_client(request_executor=fake_request).ensure_folder(name="Applications")

        self.assertTrue(result["created"])
        self.assertEqual(calls[-1]["method"], "POST")

    def test_upsert_json_file_updates_existing_file(self) -> None:
        multipart_calls: list[dict[str, object]] = []

        def fake_request(method: str, url: str, **kwargs: object) -> dict[str, object]:
            return {"files": [{"id": "file-1", "name": "job.json", "mimeType": JSON_MIME_TYPE}]}

        def fake_multipart(method: str, url: str, **kwargs: object) -> dict[str, object]:
            multipart_calls.append({"method": method, "url": url, **kwargs})
            return {"id": "file-1", "name": "job.json", "mimeType": JSON_MIME_TYPE}

        result = self._make_client(request_executor=fake_request, multipart_request_executor=fake_multipart).upsert_json_file(
            name="job.json",
            parent_id="folder-1",
            payload={"company": "Acme"},
        )

        self.assertFalse(result["created"])
        self.assertEqual(multipart_calls[0]["method"], "PATCH")

    def test_upsert_json_file_creates_when_missing(self) -> None:
        multipart_calls: list[dict[str, object]] = []

        def fake_multipart(method: str, url: str, **kwargs: object) -> dict[str, object]:
            multipart_calls.append({"method": method, "url": url, **kwargs})
            return {"id": "file-2", "name": "job.json", "mimeType": JSON_MIME_TYPE}

        result = self._make_client(multipart_request_executor=fake_multipart).upsert_json_file(
            name="job.json",
            parent_id="folder-1",
            payload={"company": "Acme"},
        )

        self.assertTrue(result["created"])
        self.assertEqual(multipart_calls[0]["method"], "POST")

    def test_copy_file_posts_to_copy_endpoint(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_request(method: str, url: str, **kwargs: object) -> dict[str, object]:
            calls.append({"method": method, "url": url, **kwargs})
            return {"id": "copy-1", "name": "job copy.json", "mimeType": JSON_MIME_TYPE}

        result = self._make_client(request_executor=fake_request).copy_file("file-1", name="job copy.json")

        self.assertEqual(result["id"], "copy-1")
        self.assertEqual(calls[0]["method"], "POST")
        self.assertIn("/copy", str(calls[0]["url"]))

    def test_move_file_uses_current_parents_when_clearing_existing(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_request(method: str, url: str, **kwargs: object) -> dict[str, object]:
            calls.append({"method": method, "url": url, **kwargs})
            if method == "GET":
                return {"id": "file-1", "parents": ["folder-1"]}
            return {"id": "file-1", "name": "job.json", "parents": ["folder-2"], "mimeType": JSON_MIME_TYPE}

        result = self._make_client(request_executor=fake_request).move_file("file-1", new_parent_id="folder-2")

        self.assertEqual(result["parents"], ["folder-2"])
        self.assertEqual(calls[-1]["method"], "PATCH")
        self.assertIn("addParents=folder-2", str(calls[-1]["url"]))
        self.assertIn("removeParents=folder-1", str(calls[-1]["url"]))

    def test_move_file_does_not_remove_destination_parent(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_request(method: str, url: str, **kwargs: object) -> dict[str, object]:
            calls.append({"method": method, "url": url, **kwargs})
            if method == "GET":
                return {"id": "file-1", "parents": ["folder-2"]}
            return {"id": "file-1", "name": "job.json", "parents": ["folder-2"], "mimeType": JSON_MIME_TYPE}

        self._make_client(request_executor=fake_request).move_file("file-1", new_parent_id="folder-2")

        self.assertNotIn("removeParents=folder-2", str(calls[-1]["url"]))

    def test_create_shortcut_posts_shortcut_metadata(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_request(method: str, url: str, **kwargs: object) -> dict[str, object]:
            calls.append({"method": method, "url": url, **kwargs})
            return {
                "id": "shortcut-1",
                "name": "Shortcut",
                "mimeType": "application/vnd.google-apps.shortcut",
            }

        result = self._make_client(request_executor=fake_request).create_shortcut(
            target_file_id="file-1",
            name="Shortcut",
        )

        self.assertEqual(result["id"], "shortcut-1")
        self.assertEqual(calls[0]["json_body"]["shortcutDetails"]["targetId"], "file-1")

    def test_list_permissions_returns_sorted_permissions(self) -> None:
        client = self._make_client(
            request_executor=lambda method, url, **kwargs: {
                "permissions": [
                    {"id": "b", "role": "writer", "type": "user"},
                    {"id": "a", "role": "commenter", "type": "user"},
                ]
            }
        )

        result = client.list_permissions("file-1")

        self.assertEqual([item["id"] for item in result], ["a", "b"])

    def test_create_permission_posts_permission_payload(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_request(method: str, url: str, **kwargs: object) -> dict[str, object]:
            calls.append({"method": method, "url": url, **kwargs})
            return {"id": "perm-1", "role": "writer", "type": "user"}

        result = self._make_client(request_executor=fake_request).create_permission(
            "file-1",
            permission={"type": "user", "role": "writer", "emailAddress": "a@example.com"},
            send_notification_email=False,
        )

        self.assertEqual(result["id"], "perm-1")
        self.assertEqual(calls[0]["json_body"]["emailAddress"], "a@example.com")
        self.assertIn("sendNotificationEmail=False", str(calls[0]["url"]))


class GoogleDriveToolsTests(unittest.TestCase):
    def test_create_google_drive_tools_returns_registerable_tuple(self) -> None:
        credentials = GoogleDriveCredentials(client_id="cid", client_secret="secret", refresh_token="refresh")
        tools = create_google_drive_tools(credentials=credentials)
        self.assertEqual(len(tools), 1)
        ToolRegistry(tools)

    def test_tool_definition_key_is_google_drive_request(self) -> None:
        credentials = GoogleDriveCredentials(client_id="cid", client_secret="secret", refresh_token="refresh")
        tools = create_google_drive_tools(credentials=credentials)
        self.assertEqual(tools[0].definition.key, GOOGLE_DRIVE_REQUEST)

    def test_tool_handler_executes_ensure_folder(self) -> None:
        client = self._make_client_for_tools()
        registry = ToolRegistry(create_google_drive_tools(client=client))

        result = registry.execute(GOOGLE_DRIVE_REQUEST, {"operation": "ensure_folder", "payload": {"name": "Applications"}})

        self.assertEqual(result.output["operation"], "ensure_folder")
        self.assertTrue(result.output["result"]["created"])

    def test_create_google_drive_tools_raises_without_credentials_or_client(self) -> None:
        with self.assertRaises(ValueError):
            create_google_drive_tools()

    def test_allowed_operations_subset(self) -> None:
        credentials = GoogleDriveCredentials(client_id="cid", client_secret="secret", refresh_token="refresh")
        tools = create_google_drive_tools(credentials=credentials, allowed_operations=["ensure_folder"])
        enum_values = tools[0].definition.input_schema["properties"]["operation"]["enum"]
        self.assertEqual(enum_values, ["ensure_folder"])

    def test_tool_handler_executes_copy_file(self) -> None:
        client = Mock()
        client.copy_file.return_value = {"id": "copy-1"}
        registry = ToolRegistry(create_google_drive_tools(client=client))

        result = registry.execute(
            GOOGLE_DRIVE_REQUEST,
            {"operation": "copy_file", "payload": {"file_id": "file-1", "name": "job copy.json"}},
        )

        self.assertEqual(result.output["operation"], "copy_file")
        client.copy_file.assert_called_once_with("file-1", name="job copy.json", parent_id=None)

    def test_tool_handler_executes_create_permission(self) -> None:
        client = Mock()
        client.create_permission.return_value = {"id": "perm-1"}
        registry = ToolRegistry(create_google_drive_tools(client=client))

        result = registry.execute(
            GOOGLE_DRIVE_REQUEST,
            {
                "operation": "create_permission",
                "payload": {
                    "file_id": "file-1",
                    "type": "user",
                    "role": "writer",
                    "email_address": "a@example.com",
                    "send_notification_email": False,
                },
            },
        )

        self.assertEqual(result.output["operation"], "create_permission")
        client.create_permission.assert_called_once_with(
            "file-1",
            permission={
                "type": "user",
                "role": "writer",
                "emailAddress": "a@example.com",
            },
            send_notification_email=False,
        )

    def _make_client_for_tools(self) -> GoogleDriveClient:
        credentials = GoogleDriveCredentials(client_id="cid", client_secret="secret", refresh_token="refresh")
        return GoogleDriveClient(
            credentials=credentials,
            request_executor=lambda method, url, **kwargs: {"files": []} if method == "GET" else {"id": "folder-1", "name": "Applications", "mimeType": FOLDER_MIME_TYPE},
            multipart_request_executor=lambda method, url, **kwargs: {"id": "file-1", "name": "job.json", "mimeType": JSON_MIME_TYPE},
            token_request_executor=lambda url, **kwargs: {"access_token": "access-123"},
        )


if __name__ == "__main__":
    unittest.main()
