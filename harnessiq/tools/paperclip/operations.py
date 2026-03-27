"""Paperclip MCP-style tool factory for the Harnessiq tool layer."""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from harnessiq.interfaces import RequestPreparingClient

from harnessiq.providers.paperclip.operations import (
    PaperclipOperation,
    build_paperclip_operation_catalog,
    get_paperclip_operation,
)
from harnessiq.shared.tools import PAPERCLIP_REQUEST, RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.paperclip.client import PaperclipClient, PaperclipCredentials


def build_paperclip_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the Paperclip request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [operation.name for operation in operations]
    return ToolDefinition(
        key=PAPERCLIP_REQUEST,
        name="paperclip_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": (
                        "The Paperclip control-plane operation to execute. Use issue and approval "
                        "operations for day-to-day agent workflow, agent operations for identity and "
                        "management, and cost/activity operations for observability."
                    ),
                },
                "path_params": {
                    "type": "object",
                    "description": "Path parameters required by the selected operation, such as company_id, issue_id, or approval_id.",
                    "additionalProperties": True,
                },
                "query": {
                    "type": "object",
                    "description": "Optional query parameters for list/filter operations.",
                    "additionalProperties": True,
                },
                "payload": {
                    "type": "object",
                    "description": "Optional JSON request body for create, update, checkout, comment, approval, and cost-reporting operations.",
                },
                "run_id": {
                    "type": "string",
                    "description": "Optional Paperclip run identifier sent as X-Paperclip-Run-Id on supported mutating operations.",
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_paperclip_tools(
    *,
    credentials: "PaperclipCredentials | None" = None,
    client: RequestPreparingClient | None = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the MCP-style Paperclip request tool backed by the provided client."""
    paperclip_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(operation.name for operation in selected)
    definition = build_paperclip_request_tool_definition(
        allowed_operations=tuple(operation.name for operation in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        operation_name = _require_operation_name(arguments, allowed_names)
        prepared = paperclip_client.prepare_request(
            operation_name,
            path_params=_optional_mapping(arguments, "path_params"),
            query=_optional_mapping(arguments, "query"),
            payload=_optional_mapping(arguments, "payload"),
            run_id=_optional_string(arguments, "run_id"),
        )
        response = paperclip_client.request_executor(
            prepared.method,
            prepared.url,
            headers=prepared.headers,
            json_body=prepared.json_body,
            timeout_seconds=paperclip_client.credentials.timeout_seconds,
        )
        return {
            "operation": prepared.operation.name,
            "method": prepared.method,
            "path": prepared.path,
            "response": response,
        }

    return (RegisteredTool(definition=definition, handler=handler),)


def _build_tool_description(operations: Sequence[PaperclipOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for operation in operations:
        grouped.setdefault(operation.category, []).append(operation.summary())

    lines = [
        "Execute authenticated Paperclip control-plane API operations.",
        "",
        "Paperclip is an orchestration layer for agent companies. Use it to inspect companies and agents, "
        "manage issue workflows, interact with approvals, query activity, and report or inspect costs.",
        "",
        "This integration is JSON-first and intentionally excludes multipart upload endpoints such as "
        "attachments and company-logo uploads.",
        "",
        "Available operations by category:",
    ]
    for category, summaries in grouped.items():
        lines.append(f"  {category}: {', '.join(summaries)}")
    lines.append(
        "\nParameter guidance: use 'path_params' for ids, 'query' for list filters, 'payload' for JSON "
        "bodies, and 'run_id' when you want Paperclip to trace a mutating call to the current heartbeat."
    )
    return "\n".join(lines)


def _select_operations(allowed: Sequence[str] | None) -> tuple[PaperclipOperation, ...]:
    if allowed is None:
        return build_paperclip_operation_catalog()
    seen: set[str] = set()
    selected: list[PaperclipOperation] = []
    for name in allowed:
        operation = get_paperclip_operation(name)
        if operation.name not in seen:
            seen.add(operation.name)
            selected.append(operation)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: RequestPreparingClient | None) -> RequestPreparingClient:
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Paperclip credentials or a Paperclip client must be provided.")
    from harnessiq.providers.paperclip.client import PaperclipClient

    return PaperclipClient(credentials=credentials)


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(f"Unsupported Paperclip operation '{value}'. Allowed: {allowed_str}.")
    return value


def _optional_mapping(arguments: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    value = arguments.get(key)
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return value


def _optional_string(arguments: Mapping[str, object], key: str) -> str | None:
    value = arguments.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"The '{key}' argument must be a string when provided.")
    return value


__all__ = [
    "build_paperclip_request_tool_definition",
    "create_paperclip_tools",
]


