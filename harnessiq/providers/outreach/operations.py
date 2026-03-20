"""Outreach operation catalog, tool definition, and MCP-style tool factory."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Mapping, Sequence
from urllib.parse import quote

from harnessiq.providers.http import join_url
from harnessiq.shared.tools import OUTREACH_REQUEST, RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.outreach.client import OutreachCredentials

from harnessiq.shared.outreach import OutreachOperation, OutreachPreparedRequest, build_outreach_operation_catalog, get_outreach_operation

def build_outreach_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the Outreach request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [op.name for op in operations]
    return ToolDefinition(
        key=OUTREACH_REQUEST,
        name="outreach_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": "Outreach operation name.",
                },
                "path_params": {
                    "type": "object",
                    "description": "Path parameters such as prospect_id, account_id, sequence_id.",
                    "additionalProperties": True,
                },
                "query": {
                    "type": "object",
                    "description": "Optional query parameters for paginated list operations.",
                    "additionalProperties": True,
                },
                "payload": {
                    "type": "object",
                    "description": "Optional JSON body for create/update operations.",
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_outreach_tools(
    *,
    credentials: "OutreachCredentials | None" = None,
    client: "Any | None" = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the MCP-style Outreach request tool backed by the provided client."""
    outreach_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(op.name for op in selected)
    definition = build_outreach_request_tool_definition(
        allowed_operations=tuple(op.name for op in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        operation_name = _require_operation_name(arguments, allowed_names)
        prepared = outreach_client.prepare_request(
            operation_name,
            path_params=_optional_mapping(arguments, "path_params"),
            query=_optional_mapping(arguments, "query"),
            payload=arguments.get("payload"),
        )
        response = outreach_client.request_executor(
            prepared.method,
            prepared.url,
            headers=prepared.headers,
            json_body=prepared.json_body,
            timeout_seconds=outreach_client.credentials.timeout_seconds,
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
    credentials: "OutreachCredentials",
    path_params: Mapping[str, object] | None,
    query: Mapping[str, object] | None,
    payload: Any | None,
) -> OutreachPreparedRequest:
    from harnessiq.providers.outreach.api import build_headers

    op = get_outreach_operation(operation_name)
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
    headers = build_headers(credentials.access_token)

    return OutreachPreparedRequest(
        operation=op,
        method=op.method,
        path=path,
        url=full_url,
        headers=headers,
        json_body=deepcopy(payload) if payload is not None else None,
    )


def _select_operations(allowed: Sequence[str] | None) -> tuple[OutreachOperation, ...]:
    if allowed is None:
        return build_outreach_operation_catalog()
    seen: set[str] = set()
    selected: list[OutreachOperation] = []
    for name in allowed:
        op = get_outreach_operation(name)
        if op.name not in seen:
            seen.add(op.name)
            selected.append(op)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: Any) -> Any:
    from harnessiq.providers.outreach.client import OutreachClient
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Outreach credentials or an Outreach client must be provided.")
    return OutreachClient(credentials=credentials)


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        raise ValueError(f"Unsupported Outreach operation '{value}'.")
    return value


def _optional_mapping(arguments: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    v = arguments.get(key)
    if v is None:
        return None
    if not isinstance(v, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return v


def _build_tool_description(operations: Sequence[OutreachOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())
    lines = ["Execute authenticated Outreach sales engagement API operations."]
    for category, summaries in grouped.items():
        lines.append(f"{category}: {', '.join(summaries)}")
    lines.append("Use 'path_params' for resource ids, 'query' for paginated lists, 'payload' for JSON bodies.")
    return "\n".join(lines)


__all__ = [
    "OUTREACH_REQUEST",
    "OutreachOperation",
    "OutreachPreparedRequest",
    "_build_prepared_request",
    "build_outreach_operation_catalog",
    "build_outreach_request_tool_definition",
    "create_outreach_tools",
    "get_outreach_operation",
]
