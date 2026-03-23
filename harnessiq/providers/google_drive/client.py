"""Google Drive deterministic file and folder client."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Protocol
from urllib import error, parse, request

from harnessiq.providers.google_drive.api import (
    FOLDER_MIME_TYPE,
    JSON_MIME_TYPE,
    build_bearer_headers,
    files_url,
)
from harnessiq.providers.http import ProviderHTTPError, RequestExecutor, request_json
from harnessiq.shared.google_drive import GoogleDriveCredentials


class TokenRequestExecutor(Protocol):
    """Callable contract for OAuth token refresh requests."""

    def __call__(
        self,
        url: str,
        *,
        form_fields: Mapping[str, str],
        timeout_seconds: float,
    ) -> Mapping[str, Any]:
        """Execute a token refresh request and return the decoded JSON response."""


class MultipartRequestExecutor(Protocol):
    """Callable contract for multipart upload requests."""

    def __call__(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        body: bytes | None = None,
        timeout_seconds: float = 60.0,
    ) -> Any:
        """Execute a raw HTTP request and return the decoded response."""


def request_oauth_token(
    url: str,
    *,
    form_fields: Mapping[str, str],
    timeout_seconds: float,
) -> Mapping[str, Any]:
    payload = parse.urlencode(dict(form_fields)).encode("utf-8")
    http_request = request.Request(
        url=url,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(http_request, timeout=timeout_seconds) as response:
            raw = response.read()
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ProviderHTTPError(
            provider="google_drive",
            message=body or exc.reason or "HTTP error",
            status_code=exc.code,
            url=url,
            body=body,
        ) from exc
    except error.URLError as exc:
        raise ProviderHTTPError(provider="google_drive", message=str(exc.reason), url=url) from exc

    decoded = json.loads(raw.decode("utf-8"))
    if not isinstance(decoded, Mapping):
        raise ProviderHTTPError(provider="google_drive", message="OAuth token endpoint returned a non-object payload.", url=url)
    return decoded


def request_bytes_json(
    method: str,
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    body: bytes | None = None,
    timeout_seconds: float = 60.0,
) -> Any:
    http_request = request.Request(url=url, data=body, method=method.upper())
    for header_name, header_value in dict(headers or {}).items():
        http_request.add_header(header_name, header_value)
    http_request.add_header("Accept", "application/json")
    try:
        with request.urlopen(http_request, timeout=timeout_seconds) as response:
            raw = response.read()
    except error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        raise ProviderHTTPError(
            provider="google_drive",
            message=response_body or exc.reason or "HTTP error",
            status_code=exc.code,
            url=url,
            body=response_body,
        ) from exc
    except error.URLError as exc:
        raise ProviderHTTPError(provider="google_drive", message=str(exc.reason), url=url) from exc
    if not raw:
        return None
    text = raw.decode("utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


@dataclass(frozen=True, slots=True)
class GoogleDriveClient:
    """Minimal Google Drive client for deterministic folder and JSON file persistence."""

    credentials: GoogleDriveCredentials
    request_executor: RequestExecutor = request_json
    token_request_executor: TokenRequestExecutor = request_oauth_token
    multipart_request_executor: MultipartRequestExecutor = request_bytes_json

    def refresh_access_token(self) -> str:
        response = self.token_request_executor(
            self.credentials.token_url,
            form_fields={
                "client_id": self.credentials.client_id,
                "client_secret": self.credentials.client_secret,
                "grant_type": "refresh_token",
                "refresh_token": self.credentials.refresh_token,
                "scope": self.credentials.scope,
            },
            timeout_seconds=self.credentials.timeout_seconds,
        )
        access_token = response.get("access_token")
        if not isinstance(access_token, str) or not access_token.strip():
            raise ProviderHTTPError(
                provider="google_drive",
                message="OAuth token response did not include a usable access_token.",
                url=self.credentials.token_url,
                body=dict(response),
            )
        return access_token

    def find_file(
        self,
        *,
        name: str,
        parent_id: str | None = None,
        mime_type: str | None = None,
    ) -> dict[str, Any] | None:
        files = self.list_files(name=name, parent_id=parent_id, mime_type=mime_type)
        return files[0] if files else None

    def list_files(
        self,
        *,
        name: str | None = None,
        parent_id: str | None = None,
        mime_type: str | None = None,
    ) -> list[dict[str, Any]]:
        access_token = self.refresh_access_token()
        query = _build_drive_query(name=name, parent_id=parent_id, mime_type=mime_type)
        response = self.request_executor(
            "GET",
            files_url(
                self.credentials.base_url,
                query={
                    "fields": "files(id,name,mimeType,parents)",
                    "pageSize": 100,
                    "q": query,
                    "spaces": "drive",
                },
            ),
            headers=build_bearer_headers(access_token),
            timeout_seconds=self.credentials.timeout_seconds,
        )
        items = response.get("files", []) if isinstance(response, Mapping) else []
        if not isinstance(items, list):
            raise ProviderHTTPError(provider="google_drive", message="Drive list response did not include a files array.")
        normalized = [dict(item) for item in items if isinstance(item, Mapping)]
        normalized.sort(key=lambda item: (str(item.get("name", "")), str(item.get("id", ""))))
        return normalized

    def ensure_folder(self, *, name: str, parent_id: str | None = None) -> dict[str, Any]:
        existing = self.find_file(name=name, parent_id=parent_id, mime_type=FOLDER_MIME_TYPE)
        if existing is not None:
            return {"created": False, "folder": existing}
        access_token = self.refresh_access_token()
        metadata: dict[str, Any] = {"mimeType": FOLDER_MIME_TYPE, "name": name}
        if parent_id is not None:
            metadata["parents"] = [parent_id]
        response = self.request_executor(
            "POST",
            files_url(self.credentials.base_url, query={"fields": "id,name,mimeType,parents"}),
            headers=build_bearer_headers(access_token),
            json_body=metadata,
            timeout_seconds=self.credentials.timeout_seconds,
        )
        if not isinstance(response, Mapping):
            raise ProviderHTTPError(provider="google_drive", message="Drive folder create response was not a JSON object.")
        return {"created": True, "folder": dict(response)}

    def upsert_json_file(
        self,
        *,
        name: str,
        parent_id: str | None,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        existing = self.find_file(name=name, parent_id=parent_id, mime_type=JSON_MIME_TYPE)
        method = "PATCH" if existing is not None else "POST"
        file_id = str(existing["id"]) if existing is not None else None
        access_token = self.refresh_access_token()
        metadata: dict[str, Any] = {"mimeType": JSON_MIME_TYPE, "name": name}
        if parent_id is not None:
            metadata["parents"] = [parent_id]
        boundary = "===============HarnessiqGoogleDriveUpload=="
        body = _build_multipart_body(boundary=boundary, metadata=metadata, payload=payload)
        response = self.multipart_request_executor(
            method,
            files_url(
                self.credentials.base_url,
                file_id=file_id,
                upload=True,
                query={"fields": "id,name,mimeType,parents", "uploadType": "multipart"},
            ),
            headers=build_bearer_headers(
                access_token,
                extra_headers={"Content-Type": f'multipart/related; boundary="{boundary}"'},
            ),
            body=body,
            timeout_seconds=self.credentials.timeout_seconds,
        )
        if not isinstance(response, Mapping):
            raise ProviderHTTPError(provider="google_drive", message="Drive file upsert response was not a JSON object.")
        return {"created": existing is None, "file": dict(response)}


def _build_drive_query(
    *,
    name: str | None,
    parent_id: str | None,
    mime_type: str | None,
) -> str:
    clauses = ["trashed = false"]
    if name is not None:
        clauses.append(f"name = '{_escape_drive_query_value(name)}'")
    if parent_id is not None:
        clauses.append(f"'{_escape_drive_query_value(parent_id)}' in parents")
    if mime_type is not None:
        clauses.append(f"mimeType = '{_escape_drive_query_value(mime_type)}'")
    return " and ".join(clauses)


def _escape_drive_query_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _build_multipart_body(
    *,
    boundary: str,
    metadata: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> bytes:
    metadata_json = json.dumps(dict(metadata), sort_keys=True)
    payload_json = json.dumps(dict(payload), indent=2, sort_keys=True)
    segments = [
        f"--{boundary}\r\n",
        "Content-Type: application/json; charset=UTF-8\r\n\r\n",
        metadata_json,
        "\r\n",
        f"--{boundary}\r\n",
        "Content-Type: application/json; charset=UTF-8\r\n\r\n",
        payload_json,
        "\r\n",
        f"--{boundary}--\r\n",
    ]
    return "".join(segments).encode("utf-8")


__all__ = [
    "GoogleDriveClient",
    "GoogleDriveCredentials",
    "MultipartRequestExecutor",
    "TokenRequestExecutor",
    "request_bytes_json",
    "request_oauth_token",
]
