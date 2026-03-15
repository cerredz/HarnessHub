"""Lemlist MCP-style tool factory for the Harnessiq tool layer."""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from harnessiq.providers.lemlist.operations import (
    LemlistOperation,
    build_lemlist_operation_catalog,
    get_lemlist_operation,
)
from harnessiq.shared.tools import LEMLIST_REQUEST, RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.lemlist.client import LemlistClient, LemlistCredentials


def build_lemlist_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the Lemlist request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [op.name for op in operations]
    return ToolDefinition(
        key=LEMLIST_REQUEST,
        name="lemlist_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": (
                        "The Lemlist operation to execute. Campaign operations manage "
                        "multi-channel sequences. Lead operations control prospect lifecycle "
                        "within campaigns. Team operations manage sender identities and settings. "
                        "Hook operations configure webhooks for event-driven automation."
                    ),
                },
                "path_params": {
                    "type": "object",
                    "description": "Path parameters such as campaign_id, lead_id, or email.",
                    "additionalProperties": True,
                },
                "query": {
                    "type": "object",
                    "description": "Optional query parameters for list and filter operations.",
                    "additionalProperties": True,
                },
                "payload": {
                    "type": "object",
                    "description": "JSON request body for create, update, and enrich operations.",
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_lemlist_tools(
    *,
    credentials: "LemlistCredentials | None" = None,
    client: "LemlistClient | None" = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the MCP-style Lemlist request tool backed by the provided client."""
    lemlist_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(op.name for op in selected)
    definition = build_lemlist_request_tool_definition(
        allowed_operations=tuple(op.name for op in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        operation_name = _require_operation_name(arguments, allowed_names)
        prepared = lemlist_client.prepare_request(
            operation_name,
            path_params=_optional_mapping(arguments, "path_params"),
            query=_optional_mapping(arguments, "query"),
            payload=arguments.get("payload"),
        )
        response = lemlist_client.request_executor(
            prepared.method,
            prepared.url,
            headers=prepared.headers,
            json_body=prepared.json_body,
            timeout_seconds=lemlist_client.credentials.timeout_seconds,
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

def _build_tool_description(operations: Sequence[LemlistOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())

    lines = [
        "Execute authenticated Lemlist multi-channel outreach automation API operations.",
        "",
        "Lemlist is a B2B sales engagement platform supporting email, LinkedIn, and custom "
        "channel outreach. Use campaign operations to create and manage multi-step sequences. "
        "Lead operations add, enrich, and move prospects through campaign steps. Team "
        "operations manage sender identities and inbox connections. Hook operations subscribe "
        "to events like replies, clicks, and unsubscribes for downstream automation.",
        "",
        "Available operations by category:",
    ]
    for category, summaries in grouped.items():
        lines.append(f"  {category}: {', '.join(summaries)}")
    lines.append(
        "\nParameter guidance: 'path_params' for ids (campaign_id, lead_id, email), "
        "'query' for list filters, 'payload' for JSON bodies on create/update/enrich."
    )
    return "\n".join(lines)


def _select_operations(allowed: Sequence[str] | None) -> tuple[LemlistOperation, ...]:
    if allowed is None:
        return build_lemlist_operation_catalog()
    seen: set[str] = set()
    selected: list[LemlistOperation] = []
    for name in allowed:
        op = get_lemlist_operation(name)
        if op.name not in seen:
            seen.add(op.name)
            selected.append(op)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: Any) -> Any:
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Lemlist credentials or a Lemlist client must be provided.")
    from harnessiq.providers.lemlist.client import LemlistClient
    return LemlistClient(credentials=credentials)


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(f"Unsupported Lemlist operation '{value}'. Allowed: {allowed_str}.")
    return value


def _optional_mapping(arguments: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    v = arguments.get(key)
    if v is None:
        return None
    if not isinstance(v, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return v


__all__ = [
    "build_lemlist_request_tool_definition",
    "create_lemlist_tools",
]
