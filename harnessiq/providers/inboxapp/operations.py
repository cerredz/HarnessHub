"""InboxApp operation catalog, tool definition, and MCP-style tool factory."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Mapping, Sequence
from urllib.parse import quote

from harnessiq.providers.http import join_url
from harnessiq.shared.tools import INBOXAPP_REQUEST, RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.inboxapp.client import InboxAppCredentials

from harnessiq.shared.inboxapp import InboxAppOperation, InboxAppPreparedRequest, build_inboxapp_operation_catalog, get_inboxapp_operation

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
                    "description": "InboxApp operation name.",
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
                    "description": "JSON body for create, update, or delete operations that accept one.",
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_inboxapp_tools(
    *,
    credentials: "InboxAppCredentials | None" = None,
    client: "Any | None" = None,
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


def _build_prepared_request(
    *,
    operation_name: str,
    credentials: "InboxAppCredentials",
    path_params: Mapping[str, object] | None,
    query: Mapping[str, object] | None,
    payload: Any | None,
) -> InboxAppPreparedRequest:
    from harnessiq.providers.inboxapp.api import build_headers

    op = get_inboxapp_operation(operation_name)
    normalized_params = {str(k): str(v) for k, v in (path_params or {}).items()}
    missing = [k for k in op.required_path_params if not normalized_params.get(k)]
    if missing:
        raise ValueError(f"Operation '{op.name}' requires path parameters: {', '.join(missing)}.")

    if op.payload_kind == "none" and payload is not None:
        raise ValueError(f"Operation '{op.name}' does not accept a payload.")
    if op.payload_required and payload is None:
        raise ValueError(f"Operation '{op.name}' requires a payload.")

    path = op.path_hint
    for key, value in normalized_params.items():
        path = path.replace(f"{{{key}}}", quote(value, safe=""))

    normalized_query = {str(k): v for k, v in query.items()} if query else None
    full_url = join_url(credentials.base_url, path, query=normalized_query)  # type: ignore[arg-type]
    headers = build_headers(credentials.api_key)

    return InboxAppPreparedRequest(
        operation=op,
        method=op.method,
        path=path,
        url=full_url,
        headers=headers,
        json_body=deepcopy(payload) if payload is not None else None,
    )


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


def _coerce_client(*, credentials: Any, client: Any) -> Any:
    from harnessiq.providers.inboxapp.client import InboxAppClient

    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either InboxApp credentials or an InboxApp client must be provided.")
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


def _build_tool_description(operations: Sequence[InboxAppOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())

    lines = [
        "Execute authenticated InboxApp messaging and workflow API operations.",
        "",
        "InboxApp exposes workflow objects such as statuses, threads, and prospects. "
        "Use status operations to manage sales stages, thread operations to inspect or "
        "create conversations, and prospect operations to fetch known prospects.",
        "",
        "Available operations by category:",
    ]
    for category, summaries in grouped.items():
        lines.append(f"  {category}: {', '.join(summaries)}")
    lines.append(
        "\nParameter guidance: use 'path_params' for resource identifiers, 'query' for "
        "supported thread-list filters, and 'payload' for create or update bodies."
    )
    return "\n".join(lines)


__all__ = [
    "INBOXAPP_REQUEST",
    "InboxAppOperation",
    "InboxAppPreparedRequest",
    "_build_prepared_request",
    "build_inboxapp_operation_catalog",
    "build_inboxapp_request_tool_definition",
    "create_inboxapp_tools",
    "get_inboxapp_operation",
]
