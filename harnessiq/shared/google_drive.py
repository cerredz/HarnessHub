"""Shared Google Drive credentials and operation metadata."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

from harnessiq.shared.providers import (
    GOOGLE_DRIVE_DEFAULT_BASE_URL,
    GOOGLE_DRIVE_DEFAULT_SCOPE,
    GOOGLE_DRIVE_DEFAULT_TOKEN_URL,
)


@dataclass(frozen=True, slots=True)
class GoogleDriveCredentials:
    """Runtime credentials for Google Drive OAuth access."""

    client_id: str
    client_secret: str
    refresh_token: str
    base_url: str = GOOGLE_DRIVE_DEFAULT_BASE_URL
    token_url: str = GOOGLE_DRIVE_DEFAULT_TOKEN_URL
    scope: str = GOOGLE_DRIVE_DEFAULT_SCOPE
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.client_id.strip():
            raise ValueError("Google Drive client_id must not be blank.")
        if not self.client_secret.strip():
            raise ValueError("Google Drive client_secret must not be blank.")
        if not self.refresh_token.strip():
            raise ValueError("Google Drive refresh_token must not be blank.")
        if not self.base_url.strip():
            raise ValueError("Google Drive base_url must not be blank.")
        if not self.token_url.strip():
            raise ValueError("Google Drive token_url must not be blank.")
        if not self.scope.strip():
            raise ValueError("Google Drive scope must not be blank.")
        if self.timeout_seconds <= 0:
            raise ValueError("Google Drive timeout_seconds must be greater than zero.")

    def masked_refresh_token(self) -> str:
        token = self.refresh_token
        if len(token) <= 6:
            return "*" * len(token)
        return f"{token[:3]}{'*' * max(1, len(token) - 6)}{token[-3:]}"

    def as_redacted_dict(self) -> dict[str, object]:
        return {
            "client_id": self.client_id,
            "client_secret_masked": "***",
            "refresh_token_masked": self.masked_refresh_token(),
            "base_url": self.base_url,
            "token_url": self.token_url,
            "scope": self.scope,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class GoogleDriveOperation:
    """Declarative metadata for one supported Google Drive operation."""

    name: str
    category: str
    summary_text: str

    def summary(self) -> str:
        return self.summary_text


_google_drive_catalog: OrderedDict[str, GoogleDriveOperation] = OrderedDict(
    (
        (
            "ensure_folder",
            GoogleDriveOperation(
                name="ensure_folder",
                category="Folders",
                summary_text="ensure_folder (create or reuse a named folder under an optional parent)",
            ),
        ),
        (
            "find_file",
            GoogleDriveOperation(
                name="find_file",
                category="Lookup",
                summary_text="find_file (find the first matching file by name, parent, and optional MIME type)",
            ),
        ),
        (
            "upsert_json_file",
            GoogleDriveOperation(
                name="upsert_json_file",
                category="Files",
                summary_text="upsert_json_file (create or replace a JSON file under an optional parent folder)",
            ),
        ),
    )
)


def build_google_drive_operation_catalog() -> tuple[GoogleDriveOperation, ...]:
    """Return the supported Google Drive operation catalog in stable order."""

    return tuple(_google_drive_catalog.values())


def get_google_drive_operation(operation_name: str) -> GoogleDriveOperation:
    """Return one supported Google Drive operation or raise a clear error."""

    operation = _google_drive_catalog.get(operation_name)
    if operation is None:
        available = ", ".join(_google_drive_catalog)
        raise ValueError(f"Unsupported Google Drive operation '{operation_name}'. Available: {available}.")
    return operation


__all__ = [
    "GoogleDriveCredentials",
    "GoogleDriveOperation",
    "build_google_drive_operation_catalog",
    "get_google_drive_operation",
]
