"""ZeroBounce operation catalog, tool definition, and MCP-style tool factory."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Mapping, Sequence
from urllib.parse import quote

from harnessiq.providers.http import join_url
from harnessiq.shared.tools import ZEROBOUNCE_REQUEST, RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.zerobounce.client import ZeroBounceCredentials

from harnessiq.shared.zerobounce import ZeroBounceOperation, ZeroBouncePreparedRequest, build_zerobounce_operation_catalog, get_zerobounce_operation

def build_zerobounce_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the ZeroBounce request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [op.name for op in operations]
    return ToolDefinition(
        key=ZEROBOUNCE_REQUEST,
        name="zerobounce_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": "ZeroBounce operation name.",
                },
                "path_params": {
                    "type": "object",
                    "description": "Path parameters (none currently required).",
                    "additionalProperties": True,
                },
                "query": {
                    "type": "object",
                    "description": (
                        "Query parameters for GET operations. For validate_email: email, ip_address. "
                        "For get_api_usage: start_date, end_date (YYYY-MM-DD). "
                        "For bulk_file_status / bulk_get_file: file_id. "
                        "For find_email: domain, first_name, last_name."
                    ),
                    "additionalProperties": True,
                },
                "payload": {
                    "type": "object",
                    "description": (
                        "JSON body for POST operations. For validate_batch: "
                        "{email_batch: [{email_address, ip_address}], timeout, activity_data}. "
                        "For bulk_send_file: {file, email_address_column, return_url, has_header_row}. "
                        "For add_filter / delete_filter: {rule, target, value}."
                    ),
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_zerobounce_tools(
    *,
    credentials: "ZeroBounceCredentials | None" = None,
    client: "Any | None" = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the MCP-style ZeroBounce request tool backed by the provided client."""
    zb_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(op.name for op in selected)
    definition = build_zerobounce_request_tool_definition(
        allowed_operations=tuple(op.name for op in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        operation_name = _require_operation_name(arguments, allowed_names)
        prepared = zb_client.prepare_request(
            operation_name,
            path_params=_optional_mapping(arguments, "path_params"),
            query=_optional_mapping(arguments, "query"),
            payload=arguments.get("payload"),
        )
        response = zb_client.request_executor(
            prepared.method,
            prepared.url,
            headers=prepared.headers,
            json_body=prepared.json_body,
            timeout_seconds=zb_client.credentials.timeout_seconds,
        )
        return {
            "operation": prepared.operation.name,
            "method": prepared.method,
            "path": prepared.path,
            "response": response,
        }

    return (RegisteredTool(definition=definition, handler=handler),)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_prepared_request(
    *,
    operation_name: str,
    credentials: "ZeroBounceCredentials",
    path_params: Mapping[str, object] | None,
    query: Mapping[str, object] | None,
    payload: Any | None,
) -> ZeroBouncePreparedRequest:
    from harnessiq.providers.zerobounce.api import build_headers

    op = get_zerobounce_operation(operation_name)
    normalized_params = {str(k): str(v) for k, v in (path_params or {}).items()}
    missing = [k for k in op.required_path_params if not normalized_params.get(k)]
    if missing:
        raise ValueError(
            f"Operation '{op.name}' requires path parameters: {', '.join(missing)}."
        )

    if op.payload_kind == "none" and payload is not None:
        raise ValueError(f"Operation '{op.name}' does not accept a payload.")
    if op.payload_required and payload is None:
        raise ValueError(f"Operation '{op.name}' requires a payload.")

    path = op.path_hint
    for key, value in normalized_params.items():
        path = path.replace(f"{{{key}}}", quote(value, safe=""))

    # Inject api_key as query parameter (ZeroBounce auth mechanism)
    caller_query = {str(k): v for k, v in query.items()} if query else {}
    merged_query: dict[str, object] = {"api_key": credentials.api_key, **caller_query}

    # Route to the correct base URL based on the operation
    base = credentials.bulk_base_url if op.use_bulk_base else credentials.base_url
    full_url = join_url(base, path, query=merged_query)  # type: ignore[arg-type]
    headers = build_headers()

    return ZeroBouncePreparedRequest(
        operation=op,
        method=op.method,
        path=path,
        url=full_url,
        headers=headers,
        json_body=deepcopy(payload) if payload is not None else None,
    )


def _select_operations(allowed: Sequence[str] | None) -> tuple[ZeroBounceOperation, ...]:
    if allowed is None:
        return build_zerobounce_operation_catalog()
    seen: set[str] = set()
    selected: list[ZeroBounceOperation] = []
    for name in allowed:
        op = get_zerobounce_operation(name)
        if op.name not in seen:
            seen.add(op.name)
            selected.append(op)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: Any) -> Any:
    from harnessiq.providers.zerobounce.client import ZeroBounceClient
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either ZeroBounce credentials or a ZeroBounce client must be provided.")
    return ZeroBounceClient(credentials=credentials)


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(
            f"Unsupported ZeroBounce operation '{value}'. Allowed: {allowed_str}."
        )
    return value


def _optional_mapping(arguments: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    v = arguments.get(key)
    if v is None:
        return None
    if not isinstance(v, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return v


def _build_tool_description(operations: Sequence[ZeroBounceOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())
    lines = ["Execute authenticated ZeroBounce email validation and intelligence API operations."]
    for category, summaries in grouped.items():
        lines.append(f"{category}: {', '.join(summaries)}")
    lines.append(
        "Use 'query' for GET filter parameters (email, file_id, dates). "
        "Use 'payload' for POST bodies. Bulk operations route to bulkapi.zerobounce.net automatically."
    )
    return "\n".join(lines)


__all__ = [
    "ZEROBOUNCE_REQUEST",
    "ZeroBounceOperation",
    "ZeroBouncePreparedRequest",
    "_build_prepared_request",
    "build_zerobounce_operation_catalog",
    "build_zerobounce_request_tool_definition",
    "create_zerobounce_tools",
    "get_zerobounce_operation",
]
