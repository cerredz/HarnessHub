"""Hunter operation catalog, tool definition, and request preparation."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any, Mapping, Sequence
from urllib.parse import quote

from harnessiq.interfaces import RequestPreparingClient
from harnessiq.providers.hunter.api import build_headers, url
from harnessiq.shared.hunter import (
    HunterOperation,
    HunterPreparedRequest,
    build_hunter_operation_catalog,
    get_hunter_operation,
)
from harnessiq.shared.tools import (
    HUNTER_REQUEST,
    RegisteredTool,
    ToolArguments,
    ToolDefinition,
    build_grouped_operation_description,
)

if TYPE_CHECKING:
    from harnessiq.shared.credentials import HunterCredentials


def build_hunter_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the Hunter request surface."""

    operations = _select_operations(allowed_operations)
    operation_names = [operation.name for operation in operations]
    return ToolDefinition(
        key=HUNTER_REQUEST,
        name="hunter_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": "Hunter operation name.",
                },
                "path_params": {
                    "type": "object",
                    "description": "Path parameters such as the Hunter lead id for resource-specific operations.",
                    "additionalProperties": True,
                },
                "query": {
                    "type": "object",
                    "description": (
                        "Query parameters for GET operations such as domain/company filters, email lookup fields, "
                        "pagination, and optional enrichment controls."
                    ),
                    "additionalProperties": True,
                },
                "payload": {
                    "type": "object",
                    "description": "JSON body for Hunter lead create and lead update operations.",
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_hunter_tools(
    *,
    credentials: "HunterCredentials | None" = None,
    client: RequestPreparingClient | None = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the MCP-style Hunter request tool backed by the provided client."""

    hunter_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(operation.name for operation in selected)
    definition = build_hunter_request_tool_definition(
        allowed_operations=tuple(operation.name for operation in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        operation_name = _require_operation_name(arguments, allowed_names)
        prepared = hunter_client.prepare_request(
            operation_name,
            path_params=_optional_mapping(arguments, "path_params"),
            query=_optional_mapping(arguments, "query"),
            payload=arguments.get("payload"),
        )
        response = hunter_client.request_executor(
            prepared.method,
            prepared.url,
            headers=prepared.headers,
            json_body=prepared.json_body,
            timeout_seconds=hunter_client.credentials.timeout_seconds,
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
    credentials: "HunterCredentials",
    path_params: Mapping[str, object] | None,
    query: Mapping[str, object] | None,
    payload: Any | None,
) -> HunterPreparedRequest:
    operation = get_hunter_operation(operation_name)
    normalized_path_params = {str(key): str(value) for key, value in (path_params or {}).items()}
    missing = [key for key in operation.required_path_params if not normalized_path_params.get(key)]
    if missing:
        raise ValueError(
            f"Operation '{operation.name}' requires path parameters: {', '.join(missing)}."
        )

    if operation.payload_kind == "none" and payload is not None:
        raise ValueError(f"Operation '{operation.name}' does not accept a payload.")
    if operation.payload_required and payload is None:
        raise ValueError(f"Operation '{operation.name}' requires a payload.")
    if payload is not None and not isinstance(payload, dict):
        raise ValueError(f"Operation '{operation.name}' requires an object payload.")

    if query is not None and not operation.allow_query:
        raise ValueError(f"Operation '{operation.name}' does not accept query parameters.")

    normalized_query = _normalize_query(query)
    _validate_required_query(operation, normalized_query)
    _validate_required_any_of_sets(operation, normalized_query)

    path = operation.path_hint
    for key, value in normalized_path_params.items():
        path = path.replace(f"{{{key}}}", quote(value, safe=""))

    merged_query: dict[str, str | int | float | bool] = {
        "api_key": credentials.api_key,
        **normalized_query,
    }

    return HunterPreparedRequest(
        operation=operation,
        method=operation.method,
        path=path,
        url=url(credentials.base_url, path, query=merged_query),
        headers=build_headers(),
        json_body=deepcopy(payload) if payload is not None else None,
    )


def _select_operations(allowed: Sequence[str] | None) -> tuple[HunterOperation, ...]:
    if allowed is None:
        return build_hunter_operation_catalog()
    seen: set[str] = set()
    selected: list[HunterOperation] = []
    for name in allowed:
        operation = get_hunter_operation(name)
        if operation.name not in seen:
            seen.add(operation.name)
            selected.append(operation)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: RequestPreparingClient | None) -> RequestPreparingClient:
    from harnessiq.providers.hunter.client import HunterClient

    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Hunter credentials or a Hunter client must be provided.")
    return HunterClient(credentials=credentials)


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(f"Unsupported Hunter operation '{value}'. Allowed: {allowed_str}.")
    return value


def _optional_mapping(arguments: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    value = arguments.get(key)
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return value


def _build_tool_description(operations: Sequence[HunterOperation]) -> str:
    return build_grouped_operation_description(
        operations,
        lead="Execute authenticated Hunter.io email discovery, verification, enrichment, and lead management API operations.",
        usage=(
            "Use discovery operations to find domains, companies, and professional emails; verification to assess deliverability; "
            "enrichment to attach person and company context; and lead/campaign operations for lightweight outbound workflow management."
        ),
        closing=(
            "Use 'path_params' for lead ids, 'query' for GET filters, and 'payload' for lead create/update request bodies. "
            "Hunter authentication is always injected as the 'api_key' query parameter."
        ),
    )


def _normalize_query(
    query: Mapping[str, object] | None,
) -> dict[str, str | int | float | bool]:
    if query is None:
        return {}
    return {str(key): value for key, value in query.items() if _has_value(value)}


def _validate_required_query(
    operation: HunterOperation,
    query: Mapping[str, object],
) -> None:
    missing = [field_name for field_name in operation.required_query_params if not _has_value(query.get(field_name))]
    if missing:
        raise ValueError(
            f"Operation '{operation.name}' requires query parameters: {', '.join(missing)}."
        )


def _validate_required_any_of_sets(
    operation: HunterOperation,
    query: Mapping[str, object],
) -> None:
    for option_set in operation.required_any_of_sets:
        if any(all(_has_value(query.get(field_name)) for field_name in combination) for combination in option_set):
            continue
        rendered = " or ".join(
            " + ".join(field_name for field_name in combination)
            for combination in option_set
        )
        raise ValueError(
            f"Operation '{operation.name}' requires one of: {rendered}."
        )


def _has_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


__all__ = [
    "HUNTER_REQUEST",
    "HunterOperation",
    "HunterPreparedRequest",
    "_build_prepared_request",
    "build_hunter_operation_catalog",
    "build_hunter_request_tool_definition",
    "create_hunter_tools",
    "get_hunter_operation",
]
