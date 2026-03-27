"""Shared Google Drive credentials and operation metadata."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass

from harnessiq.shared.provider_payloads import (
    optional_payload_bool,
    optional_payload_string,
    require_payload_string,
)
from harnessiq.shared.providers import (
    GOOGLE_DRIVE_DEFAULT_BASE_URL,
    GOOGLE_DRIVE_DEFAULT_SCOPE,
    GOOGLE_DRIVE_DEFAULT_TOKEN_URL,
)
from harnessiq.shared.validated import HttpUrl, NonEmptyString, parse_positive_number


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
        object.__setattr__(self, "client_id", NonEmptyString(self.client_id, field_name="Google Drive client_id"))
        object.__setattr__(
            self,
            "client_secret",
            NonEmptyString(self.client_secret, field_name="Google Drive client_secret"),
        )
        object.__setattr__(
            self,
            "refresh_token",
            NonEmptyString(self.refresh_token, field_name="Google Drive refresh_token"),
        )
        object.__setattr__(self, "base_url", HttpUrl(self.base_url, field_name="Google Drive base_url"))
        object.__setattr__(self, "token_url", HttpUrl(self.token_url, field_name="Google Drive token_url"))
        object.__setattr__(self, "scope", NonEmptyString(self.scope, field_name="Google Drive scope"))
        object.__setattr__(
            self,
            "timeout_seconds",
            parse_positive_number(self.timeout_seconds, field_name="Google Drive timeout_seconds"),
        )

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
    payload_description: str

    def summary(self) -> str:
        return self.summary_text

    def payload_summary(self) -> str:
        return self.payload_description


def _operation(
    name: str,
    category: str,
    summary_text: str,
    payload_description: str,
) -> tuple[str, GoogleDriveOperation]:
    """Build one catalog entry so operation metadata stays concise and consistent."""
    return (
        name,
        GoogleDriveOperation(
            name=name,
            category=category,
            summary_text=summary_text,
            payload_description=payload_description,
        ),
    )


_google_drive_catalog: OrderedDict[str, GoogleDriveOperation] = OrderedDict(
    (
        _operation(
            "ensure_folder",
            "Folders",
            "ensure_folder (create or reuse a named folder under an optional parent)",
            "{name, parent_id?}",
        ),
        _operation(
            "list_files",
            "Lookup",
            "list_files (list files by optional name, parent, MIME type, or raw Drive query)",
            "{name?, parent_id?, mime_type?, query?, page_size?, include_trashed?}",
        ),
        _operation(
            "find_file",
            "Lookup",
            "find_file (find the first matching file by name, parent, and optional MIME type)",
            "{name, parent_id?, mime_type?}",
        ),
        _operation(
            "get_file",
            "Lookup",
            "get_file (fetch one file's metadata by id)",
            "{file_id}",
        ),
        _operation(
            "upsert_json_file",
            "Files",
            "upsert_json_file (create or replace a JSON file under an optional parent folder)",
            "{name, parent_id?, payload}",
        ),
        _operation(
            "copy_file",
            "Files",
            "copy_file (duplicate one Drive file, optionally renaming it or placing it in another folder)",
            "{file_id, name?, parent_id?}",
        ),
        _operation(
            "move_file",
            "Files",
            "move_file (move one file to a new folder and optionally rename it)",
            "{file_id, new_parent_id?, remove_parent_ids?, clear_existing_parents?, name?}",
        ),
        _operation(
            "create_shortcut",
            "Shortcuts",
            "create_shortcut (create a Drive shortcut that points at another file or folder)",
            "{target_file_id, name?, parent_id?}",
        ),
        _operation(
            "list_permissions",
            "Permissions",
            "list_permissions (list the current sharing permissions for a file)",
            "{file_id}",
        ),
        _operation(
            "create_permission",
            "Permissions",
            "create_permission (grant a new sharing permission to a file)",
            "{file_id, type, role, email_address?, domain?, allow_file_discovery?, send_notification_email?}",
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


def build_google_drive_permission_payload(payload: Mapping[str, object]) -> dict[str, object]:
    """Normalize the Google Drive permission payload from a DTO request envelope."""

    permission = {
        "type": require_payload_string(payload, "type"),
        "role": require_payload_string(payload, "role"),
    }
    email_address = optional_payload_string(payload, "email_address")
    if email_address is not None:
        permission["emailAddress"] = email_address
    domain = optional_payload_string(payload, "domain")
    if domain is not None:
        permission["domain"] = domain
    allow_file_discovery = optional_payload_bool(payload, "allow_file_discovery")
    if allow_file_discovery is not None:
        permission["allowFileDiscovery"] = allow_file_discovery
    return permission


__all__ = [
    "build_google_drive_permission_payload",
    "GoogleDriveCredentials",
    "GoogleDriveOperation",
    "build_google_drive_operation_catalog",
    "get_google_drive_operation",
]
