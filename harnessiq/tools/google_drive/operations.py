"""Google Drive MCP-style tool factory for the Harnessiq tool layer."""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from harnessiq.providers.google_drive.operations import (
    GoogleDriveOperation,
    build_google_drive_operation_catalog,
    get_google_drive_operation,
)
from harnessiq.shared.tools import GOOGLE_DRIVE_REQUEST, RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.google_drive.client import GoogleDriveClient, GoogleDriveCredentials


def build_google_drive_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    operations = _select_operations(allowed_operations)
    operation_names = [operation.name for operation in operations]
    return ToolDefinition(
        key=GOOGLE_DRIVE_REQUEST,
        name="google_drive_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": "Google Drive operation name.",
                },
                "payload": {
                    "type": "object",
                    "description": (
                        "Operation payload. For ensure_folder: {name, parent_id?}. "
                        "For find_file: {name, parent_id?, mime_type?}. "
                        "For upsert_json_file: {name, parent_id?, payload}."
                    ),
                    "additionalProperties": True,
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_google_drive_tools(
    *,
    credentials: "GoogleDriveCredentials | None" = None,
    client: "GoogleDriveClient | None" = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    google_drive_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(operation.name for operation in selected)
    definition = build_google_drive_request_tool_definition(
        allowed_operations=tuple(operation.name for operation in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        operation_name = _require_operation_name(arguments, allowed_names)
        payload = dict(_optional_mapping(arguments, "payload") or {})
        if operation_name == "ensure_folder":
            name = _require_string(payload, "name")
            parent_id = _optional_string(payload, "parent_id")
            result = google_drive_client.ensure_folder(name=name, parent_id=parent_id)
        elif operation_name == "find_file":
            name = _require_string(payload, "name")
            result = google_drive_client.find_file(
                name=name,
                parent_id=_optional_string(payload, "parent_id"),
                mime_type=_optional_string(payload, "mime_type"),
            )
        else:
            name = _require_string(payload, "name")
            file_payload = payload.get("payload")
            if not isinstance(file_payload, Mapping):
                raise ValueError("The 'payload.payload' field must be an object for upsert_json_file.")
            result = google_drive_client.upsert_json_file(
                name=name,
                parent_id=_optional_string(payload, "parent_id"),
                payload={str(key): value for key, value in file_payload.items()},
            )
        return {"operation": operation_name, "result": result}

    return (RegisteredTool(definition=definition, handler=handler),)


def _build_tool_description(operations: Sequence[GoogleDriveOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for operation in operations:
        grouped.setdefault(operation.category, []).append(operation.summary())
    lines = ["Execute authenticated Google Drive folder lookup/create and JSON file upsert operations."]
    for category, summaries in grouped.items():
        lines.append(f"{category}: {', '.join(summaries)}")
    lines.append("Use the payload object for operation-specific arguments. OAuth token refresh is handled internally.")
    return "\n".join(lines)


def _select_operations(allowed: Sequence[str] | None) -> tuple[GoogleDriveOperation, ...]:
    if allowed is None:
        return build_google_drive_operation_catalog()
    seen: set[str] = set()
    selected: list[GoogleDriveOperation] = []
    for name in allowed:
        operation = get_google_drive_operation(name)
        if operation.name not in seen:
            seen.add(operation.name)
            selected.append(operation)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: Any) -> Any:
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Google Drive credentials or a Google Drive client must be provided.")
    from harnessiq.providers.google_drive.client import GoogleDriveClient
    return GoogleDriveClient(credentials=credentials)


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(f"Unsupported Google Drive operation '{value}'. Allowed: {allowed_str}.")
    return value


def _optional_mapping(arguments: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    value = arguments.get(key)
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return value


def _require_string(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"The '{key}' field must be a non-empty string.")
    return value


def _optional_string(payload: Mapping[str, object], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"The '{key}' field must be a string when provided.")
    normalized = value.strip()
    return normalized or None


__all__ = [
    "build_google_drive_request_tool_definition",
    "create_google_drive_tools",
]
