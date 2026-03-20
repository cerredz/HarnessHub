"""Expandi operation catalog, tool definition, and MCP-style tool factory."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Mapping, Sequence
from urllib.parse import quote

from harnessiq.providers.http import join_url
from harnessiq.shared.tools import EXPANDI_REQUEST, RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.expandi.client import ExpandiCredentials

from harnessiq.shared.expandi import ExpandiOperation, ExpandiPreparedRequest, build_expandi_operation_catalog, get_expandi_operation

def build_expandi_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the Expandi request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [op.name for op in operations]
    return ToolDefinition(
        key=EXPANDI_REQUEST,
        name="expandi_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": "Expandi operation name.",
                },
                "path_params": {
                    "type": "object",
                    "description": "Path parameters such as campaign_id, contact_id, account_id, action_id.",
                    "additionalProperties": True,
                },
                "query": {
                    "type": "object",
                    "description": "Optional query parameters (e.g. workspace_id, page for list_linkedin_accounts_v2).",
                    "additionalProperties": True,
                },
                "payload": {
                    "type": "object",
                    "description": "JSON body for POST/PATCH/DELETE operations.",
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_expandi_tools(
    *,
    credentials: "ExpandiCredentials | None" = None,
    client: "Any | None" = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the MCP-style Expandi request tool backed by the provided client."""
    expandi_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(op.name for op in selected)
    definition = build_expandi_request_tool_definition(
        allowed_operations=tuple(op.name for op in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        operation_name = _require_operation_name(arguments, allowed_names)
        prepared = expandi_client.prepare_request(
            operation_name,
            path_params=_optional_mapping(arguments, "path_params"),
            query=_optional_mapping(arguments, "query"),
            payload=arguments.get("payload"),
        )
        response = expandi_client.request_executor(
            prepared.method,
            prepared.url,
            headers=prepared.headers,
            json_body=prepared.json_body,
            timeout_seconds=expandi_client.credentials.timeout_seconds,
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
    credentials: "ExpandiCredentials",
    path_params: Mapping[str, object] | None,
    query: Mapping[str, object] | None,
    payload: Any | None,
) -> ExpandiPreparedRequest:
    from harnessiq.providers.expandi.api import build_headers

    op = get_expandi_operation(operation_name)
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

    # Inject key + secret as query parameters (Expandi auth mechanism)
    caller_query = {str(k): v for k, v in query.items()} if query else {}
    merged_query: dict[str, object] = {
        "key": credentials.api_key,
        "secret": credentials.api_secret,
        **caller_query,
    }

    full_url = join_url(credentials.base_url, path, query=merged_query)  # type: ignore[arg-type]
    headers = build_headers()

    return ExpandiPreparedRequest(
        operation=op,
        method=op.method,
        path=path,
        url=full_url,
        headers=headers,
        json_body=deepcopy(payload) if payload is not None else None,
    )


def _select_operations(allowed: Sequence[str] | None) -> tuple[ExpandiOperation, ...]:
    if allowed is None:
        return build_expandi_operation_catalog()
    seen: set[str] = set()
    selected: list[ExpandiOperation] = []
    for name in allowed:
        op = get_expandi_operation(name)
        if op.name not in seen:
            seen.add(op.name)
            selected.append(op)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: Any) -> Any:
    from harnessiq.providers.expandi.client import ExpandiClient
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Expandi credentials or an Expandi client must be provided.")
    return ExpandiClient(credentials=credentials)


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(
            f"Unsupported Expandi operation '{value}'. Allowed: {allowed_str}."
        )
    return value


def _optional_mapping(arguments: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    v = arguments.get(key)
    if v is None:
        return None
    if not isinstance(v, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return v


def _build_tool_description(operations: Sequence[ExpandiOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())
    lines = ["Execute authenticated Expandi LinkedIn outreach automation API operations."]
    for category, summaries in grouped.items():
        lines.append(f"{category}: {', '.join(summaries)}")
    lines.append(
        "Use 'path_params' for resource ids (campaign_id, contact_id, account_id, action_id). "
        "'query' for list filters. 'payload' for prospect data and message bodies."
    )
    return "\n".join(lines)


__all__ = [
    "EXPANDI_REQUEST",
    "ExpandiOperation",
    "ExpandiPreparedRequest",
    "_build_prepared_request",
    "build_expandi_operation_catalog",
    "build_expandi_request_tool_definition",
    "create_expandi_tools",
    "get_expandi_operation",
]
