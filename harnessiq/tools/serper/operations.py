"""Serper MCP-style tool factory for the Harnessiq tool layer."""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from harnessiq.interfaces import RequestPreparingClient

from harnessiq.providers.serper.operations import (
    SerperOperation,
    build_serper_operation_catalog,
    get_serper_operation,
)
from harnessiq.shared.tools import RegisteredTool, SERPER_REQUEST, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.serper.client import SerperClient, SerperCredentials


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
                    "description": (
                        "The Serper search mode to execute, such as search, news, maps, or scholar."
                    ),
                },
                "payload": {
                    "type": "object",
                    "description": (
                        "JSON request body for the Serper mode. Typically includes 'q' and "
                        "may include localization, pagination, or mode-specific fields."
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
    client: RequestPreparingClient | None = None,
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


def _build_tool_description(operations: Sequence[SerperOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())

    lines = [
        "Execute authenticated Serper search API operations.",
        "",
        "Serper exposes multiple Google result modes through one API surface. This tool "
        "keeps the initial provider conservative around visible search, maps, autocomplete, "
        "and research-oriented modes.",
        "",
        "Available operations by category:",
    ]
    for category, summaries in grouped.items():
        lines.append(f"  {category}: {', '.join(summaries)}")
    lines.append(
        "\nParameter guidance: every request sends a JSON 'payload', usually with 'q' and "
        "optional localization or mode-specific fields."
    )
    return "\n".join(lines)


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


def _coerce_client(*, credentials: Any, client: RequestPreparingClient | None) -> RequestPreparingClient:
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Serper credentials or a Serper client must be provided.")
    from harnessiq.providers.serper.client import SerperClient
    return SerperClient(credentials=credentials)


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(f"Unsupported Serper operation '{value}'. Allowed: {allowed_str}.")
    return value


__all__ = [
    "build_serper_request_tool_definition",
    "create_serper_tools",
]


