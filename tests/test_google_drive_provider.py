"""Tests for harnessiq.providers.google_drive."""

from __future__ import annotations

import unittest

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
        self.assertEqual(names, ["ensure_folder", "find_file", "upsert_json_file"])

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
