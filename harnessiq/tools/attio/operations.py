"""Attio MCP-style tool factory for the Harnessiq tool layer."""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from harnessiq.interfaces import RequestPreparingClient

from harnessiq.providers.attio.operations import (
    AttioOperation,
    build_attio_operation_catalog,
    get_attio_operation,
)
from harnessiq.shared.tools import ATTIO_REQUEST, RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.attio.client import AttioClient, AttioCredentials


def build_attio_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the Attio request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [op.name for op in operations]
    return ToolDefinition(
        key=ATTIO_REQUEST,
        name="attio_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": (
                        "The Attio operation to execute. Object operations inspect workspace "
                        "schema, attribute operations inspect fields, and record operations "
                        "query or mutate CRM records."
                    ),
                },
                "path_params": {
                    "type": "object",
                    "description": (
                        "Path parameters such as object, record_id, target, and identifier."
                    ),
                    "additionalProperties": True,
                },
                "query": {
                    "type": "object",
                    "description": "Optional query parameters for supported list endpoints.",
                    "additionalProperties": True,
                },
                "payload": {
                    "type": "object",
                    "description": "JSON request body for list/create/assert record operations.",
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_attio_tools(
    *,
    credentials: "AttioCredentials | None" = None,
    client: RequestPreparingClient | None = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the MCP-style Attio request tool backed by the provided client."""
    attio_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(op.name for op in selected)
    definition = build_attio_request_tool_definition(
        allowed_operations=tuple(op.name for op in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        operation_name = _require_operation_name(arguments, allowed_names)
        prepared = attio_client.prepare_request(
            operation_name,
            path_params=_optional_mapping(arguments, "path_params"),
            query=_optional_mapping(arguments, "query"),
            payload=arguments.get("payload"),
        )
        response = attio_client.request_executor(
            prepared.method,
            prepared.url,
            headers=prepared.headers,
            json_body=prepared.json_body,
            timeout_seconds=attio_client.credentials.timeout_seconds,
        )
        return {
            "operation": prepared.operation.name,
            "method": prepared.method,
            "path": prepared.path,
            "response": response,
        }

    return (RegisteredTool(definition=definition, handler=handler),)


def _build_tool_description(operations: Sequence[AttioOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())

    lines = [
        "Execute authenticated Attio CRM API operations.",
        "",
        "Attio is a record-centric CRM. Use object operations to inspect workspace schema, "
        "attribute operations to inspect field definitions, and record operations to query "
        "or mutate Attio records.",
        "",
        "Available operations by category:",
    ]
    for category, summaries in grouped.items():
        lines.append(f"  {category}: {', '.join(summaries)}")
    lines.append(
        "\nParameter guidance: pass resource identifiers through 'path_params', optional "
        "filters through 'query', and request bodies through 'payload'."
    )
    return "\n".join(lines)


def _select_operations(allowed: Sequence[str] | None) -> tuple[AttioOperation, ...]:
    if allowed is None:
        return build_attio_operation_catalog()
    seen: set[str] = set()
    selected: list[AttioOperation] = []
    for name in allowed:
        op = get_attio_operation(name)
        if op.name not in seen:
            seen.add(op.name)
            selected.append(op)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: RequestPreparingClient | None) -> RequestPreparingClient:
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Attio credentials or an Attio client must be provided.")
    from harnessiq.providers.attio.client import AttioClient
    return AttioClient(credentials=credentials)


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(f"Unsupported Attio operation '{value}'. Allowed: {allowed_str}.")
    return value


def _optional_mapping(arguments: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    value = arguments.get(key)
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return value


__all__ = [
    "build_attio_request_tool_definition",
    "create_attio_tools",
]


