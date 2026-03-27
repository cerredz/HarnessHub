"""InboxApp MCP-style tool factory for the Harnessiq tool layer."""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from harnessiq.interfaces import RequestPreparingClient

from harnessiq.providers.inboxapp.operations import (
    InboxAppOperation,
    build_inboxapp_operation_catalog,
    get_inboxapp_operation,
)
from harnessiq.shared.tools import INBOXAPP_REQUEST, RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.inboxapp.client import InboxAppClient, InboxAppCredentials


def build_inboxapp_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the InboxApp request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [op.name for op in operations]
    return ToolDefinition(
        key=INBOXAPP_REQUEST,
        name="inboxapp_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": (
                        "The InboxApp operation to execute. Status operations manage sales "
                        "stages, thread operations manage conversation records, and prospect "
                        "operations fetch known prospect profiles."
                    ),
                },
                "path_params": {
                    "type": "object",
                    "description": "Path parameters such as status_id, thread_id, and prospect_id.",
                    "additionalProperties": True,
                },
                "query": {
                    "type": "object",
                    "description": "Optional query parameters for supported list operations.",
                    "additionalProperties": True,
                },
                "payload": {
                    "type": "object",
                    "description": "JSON request body for create, update, or delete operations that accept one.",
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_inboxapp_tools(
    *,
    credentials: "InboxAppCredentials | None" = None,
    client: RequestPreparingClient | None = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the MCP-style InboxApp request tool backed by the provided client."""
    inboxapp_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(op.name for op in selected)
    definition = build_inboxapp_request_tool_definition(
        allowed_operations=tuple(op.name for op in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        operation_name = _require_operation_name(arguments, allowed_names)
        prepared = inboxapp_client.prepare_request(
            operation_name,
            path_params=_optional_mapping(arguments, "path_params"),
            query=_optional_mapping(arguments, "query"),
            payload=arguments.get("payload"),
        )
        response = inboxapp_client.request_executor(
            prepared.method,
            prepared.url,
            headers=prepared.headers,
            json_body=prepared.json_body,
            timeout_seconds=inboxapp_client.credentials.timeout_seconds,
        )
        return {
            "operation": prepared.operation.name,
            "method": prepared.method,
            "path": prepared.path,
            "response": response,
        }

    return (RegisteredTool(definition=definition, handler=handler),)


def _build_tool_description(operations: Sequence[InboxAppOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())

    lines = [
        "Execute authenticated InboxApp API operations.",
        "",
        "InboxApp exposes statuses, threads, and prospects through a bearer-authenticated API. "
        "Use statuses to model workflow stages, threads to inspect conversations, and prospects "
        "to fetch linked prospect records.",
        "",
        "Available operations by category:",
    ]
    for category, summaries in grouped.items():
        lines.append(f"  {category}: {', '.join(summaries)}")
    lines.append(
        "\nParameter guidance: use 'path_params' for resource ids, optional 'query' for list "
        "filters, and 'payload' for create or update bodies."
    )
    return "\n".join(lines)


def _select_operations(allowed: Sequence[str] | None) -> tuple[InboxAppOperation, ...]:
    if allowed is None:
        return build_inboxapp_operation_catalog()
    seen: set[str] = set()
    selected: list[InboxAppOperation] = []
    for name in allowed:
        op = get_inboxapp_operation(name)
        if op.name not in seen:
            seen.add(op.name)
            selected.append(op)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: RequestPreparingClient | None) -> RequestPreparingClient:
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either InboxApp credentials or an InboxApp client must be provided.")
    from harnessiq.providers.inboxapp.client import InboxAppClient
    return InboxAppClient(credentials=credentials)


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(f"Unsupported InboxApp operation '{value}'. Allowed: {allowed_str}.")
    return value


def _optional_mapping(arguments: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    value = arguments.get(key)
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return value


__all__ = [
    "build_inboxapp_request_tool_definition",
    "create_inboxapp_tools",
]


