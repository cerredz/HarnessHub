"""Google Drive API constants and authentication helpers."""

from __future__ import annotations

from typing import Mapping
from urllib.parse import quote

from harnessiq.providers.http import join_url
from harnessiq.shared.providers import (
    GOOGLE_DRIVE_DEFAULT_BASE_URL as DEFAULT_BASE_URL,
    GOOGLE_DRIVE_DEFAULT_SCOPE as DEFAULT_SCOPE,
    GOOGLE_DRIVE_DEFAULT_TOKEN_URL as DEFAULT_TOKEN_URL,
    GOOGLE_DRIVE_FILES_PATH as DRIVE_FILES_PATH,
    GOOGLE_DRIVE_FOLDER_MIME_TYPE as FOLDER_MIME_TYPE,
    GOOGLE_DRIVE_JSON_MIME_TYPE as JSON_MIME_TYPE,
    GOOGLE_DRIVE_UPLOAD_FILES_PATH as DRIVE_UPLOAD_FILES_PATH,
)

SHORTCUT_MIME_TYPE = "application/vnd.google-apps.shortcut"


def build_bearer_headers(
    access_token: str,
    *,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, str]:
    headers: dict[str, str] = {"Authorization": f"Bearer {access_token}"}
    if extra_headers:
        headers.update(extra_headers)
    return headers


def files_url(
    base_url: str,
    *,
    file_id: str | None = None,
    upload: bool = False,
    query: Mapping[str, str | int | float | bool] | None = None,
) -> str:
    path = DRIVE_UPLOAD_FILES_PATH if upload else DRIVE_FILES_PATH
    if file_id:
        path = f"{path}/{quote(file_id, safe='')}"
    return join_url(base_url, path, query=query)


def file_action_url(
    base_url: str,
    *,
    file_id: str,
    action: str,
    query: Mapping[str, str | int | float | bool] | None = None,
) -> str:
    path = f"{DRIVE_FILES_PATH}/{quote(file_id, safe='')}/{quote(action, safe='')}"
    return join_url(base_url, path, query=query)


def permissions_url(
    base_url: str,
    *,
    file_id: str,
    query: Mapping[str, str | int | float | bool] | None = None,
) -> str:
    path = f"{DRIVE_FILES_PATH}/{quote(file_id, safe='')}/permissions"
    return join_url(base_url, path, query=query)
