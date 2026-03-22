"""Google Drive operation catalog for deterministic folder and JSON file writes."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GoogleDriveOperation:
    """Declarative metadata for one supported Google Drive operation."""

    name: str
    category: str
    summary_text: str

    def summary(self) -> str:
        return self.summary_text


_GOOGLE_DRIVE_CATALOG: OrderedDict[str, GoogleDriveOperation] = OrderedDict(
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
    return tuple(_GOOGLE_DRIVE_CATALOG.values())


def get_google_drive_operation(operation_name: str) -> GoogleDriveOperation:
    operation = _GOOGLE_DRIVE_CATALOG.get(operation_name)
    if operation is None:
        available = ", ".join(_GOOGLE_DRIVE_CATALOG)
        raise ValueError(f"Unsupported Google Drive operation '{operation_name}'. Available: {available}.")
    return operation


__all__ = [
    "GoogleDriveOperation",
    "build_google_drive_operation_catalog",
    "get_google_drive_operation",
]
