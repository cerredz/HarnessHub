"""Serper operation catalog, tool definition, and MCP-style tool factory."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Mapping, Sequence

from harnessiq.providers.http import join_url
from harnessiq.shared.tools import RegisteredTool, SERPER_REQUEST, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.serper.client import SerperCredentials

from harnessiq.shared.serper import SerperOperation, SerperPreparedRequest, build_serper_operation_catalog, get_serper_operation

def build_serper_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the Serper request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [op.name for op in operations]
    return ToolDefinition(
        key=SERPER_REQUEST,
        name="serper_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": "Serper search mode to execute.",
                },
                "payload": {
                    "type": "object",
                    "description": (
                        "JSON body for the Serper request. Typically includes 'q' and may "
                        "include 'gl', 'hl', 'num', and mode-specific parameters."
                    ),
                },
            },
            "required": ["operation", "payload"],
            "additionalProperties": False,
        },
    )


def create_serper_tools(
    *,
    credentials: "SerperCredentials | None" = None,
    client: "Any | None" = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the MCP-style Serper request tool backed by the provided client."""
    serper_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(op.name for op in selected)
    definition = build_serper_request_tool_definition(
        allowed_operations=tuple(op.name for op in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        operation_name = _require_operation_name(arguments, allowed_names)
        prepared = serper_client.prepare_request(
            operation_name,
            payload=arguments.get("payload"),
        )
        response = serper_client.request_executor(
            prepared.method,
            prepared.url,
            headers=prepared.headers,
            json_body=prepared.json_body,
            timeout_seconds=serper_client.credentials.timeout_seconds,
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
    credentials: "SerperCredentials",
    path_params: Mapping[str, object] | None,
    query: Mapping[str, object] | None,
    payload: Any | None,
) -> SerperPreparedRequest:
    from harnessiq.providers.serper.api import build_headers

    if path_params:
        raise ValueError("Serper operations do not accept path parameters.")
    if query:
        raise ValueError("Serper operations do not accept URL query parameters.")

    op = get_serper_operation(operation_name)
    if payload is None:
        raise ValueError(f"Operation '{op.name}' requires a payload.")

    full_url = join_url(credentials.base_url, op.path_hint)
    headers = build_headers(credentials.api_key)

    return SerperPreparedRequest(
        operation=op,
        method=op.method,
        path=op.path_hint,
        url=full_url,
        headers=headers,
        json_body=deepcopy(payload),
    )


def _select_operations(allowed: Sequence[str] | None) -> tuple[SerperOperation, ...]:
    if allowed is None:
        return build_serper_operation_catalog()
    seen: set[str] = set()
    selected: list[SerperOperation] = []
    for name in allowed:
        op = get_serper_operation(name)
        if op.name not in seen:
            seen.add(op.name)
            selected.append(op)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: Any) -> Any:
    from harnessiq.providers.serper.client import SerperClient

    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Serper credentials or a Serper client must be provided.")
    return SerperClient(credentials=credentials)


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(f"Unsupported Serper operation '{value}'. Allowed: {allowed_str}.")
    return value


def _build_tool_description(operations: Sequence[SerperOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())

    lines = [
        "Execute authenticated Serper Google search API operations.",
        "",
        "Serper exposes multiple Google result modes through a single API product. "
        "This tool keeps the initial surface conservative around core search, maps, "
        "autocomplete, and research-oriented modes visible in the public product surface.",
        "",
        "Available operations by category:",
    ]
    for category, summaries in grouped.items():
        lines.append(f"  {category}: {', '.join(summaries)}")
    lines.append(
        "\nParameter guidance: all Serper requests send a JSON 'payload', typically with "
        "'q' plus optional localization and mode-specific fields."
    )
    return "\n".join(lines)


__all__ = [
    "SERPER_REQUEST",
    "SerperOperation",
    "SerperPreparedRequest",
    "_build_prepared_request",
    "build_serper_operation_catalog",
    "build_serper_request_tool_definition",
    "create_serper_tools",
    "get_serper_operation",
]
