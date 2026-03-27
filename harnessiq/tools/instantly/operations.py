"""Instantly MCP-style tool factory for the Harnessiq tool layer."""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from harnessiq.interfaces import RequestPreparingClient
from harnessiq.shared.dtos import ProviderOperationRequestDTO

from harnessiq.providers.instantly.operations import (
    InstantlyOperation,
    build_instantly_operation_catalog,
    get_instantly_operation,
)
from harnessiq.shared.tools import INSTANTLY_REQUEST, RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.instantly.client import InstantlyClient, InstantlyCredentials


def build_instantly_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the Instantly request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [op.name for op in operations]
    return ToolDefinition(
        key=INSTANTLY_REQUEST,
        name="instantly_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": (
                        "The Instantly operation to execute. Account operations manage sending "
                        "mailboxes. Campaign operations control outreach sequences. Lead "
                        "operations add, update, and track prospects. Analytics operations "
                        "report on campaign and account performance."
                    ),
                },
                "path_params": {
                    "type": "object",
                    "description": (
                        "Path parameters for the operation URL, typically a resource id "
                        "such as campaign_id, lead_id, account_id, or api_key_id."
                    ),
                    "additionalProperties": True,
                },
                "query": {
                    "type": "object",
                    "description": "Optional query parameters for list and filter operations (pagination, status).",
                    "additionalProperties": True,
                },
                "payload": {
                    "type": "object",
                    "description": "JSON request body for create and update operations.",
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_instantly_tools(
    *,
    credentials: "InstantlyCredentials | None" = None,
    client: RequestPreparingClient | None = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the MCP-style Instantly request tool backed by the provided client."""
    instantly_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(op.name for op in selected)
    definition = build_instantly_request_tool_definition(
        allowed_operations=tuple(op.name for op in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        request = ProviderOperationRequestDTO(
            operation=_require_operation_name(arguments, allowed_names),
            path_params=_optional_mapping(arguments, "path_params") or {},
            query=_optional_mapping(arguments, "query") or {},
            payload=arguments.get("payload"),
        )
        return instantly_client.execute_operation(request).to_dict()

    return (RegisteredTool(definition=definition, handler=handler),)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_tool_description(operations: Sequence[InstantlyOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())

    lines = [
        "Execute authenticated Instantly cold email outreach automation API operations.",
        "",
        "Instantly is a cold email platform for high-volume outbound sales. Use account "
        "operations to manage sending mailboxes and warm-up settings. Campaign operations "
        "control the lifecycle of email sequences (create, activate, pause, archive). Lead "
        "operations add and manage prospects within campaigns. Analytics operations surface "
        "open, reply, and bounce rates. Webhook operations configure event notifications.",
        "",
        "Available operations by category:",
    ]
    for category, summaries in grouped.items():
        lines.append(f"  {category}: {', '.join(summaries)}")
    lines.append(
        "\nParameter guidance: 'path_params' for resource ids (campaign_id, lead_id, etc.), "
        "'query' for list pagination and status filters, 'payload' for JSON bodies."
    )
    return "\n".join(lines)


def _select_operations(allowed: Sequence[str] | None) -> tuple[InstantlyOperation, ...]:
    if allowed is None:
        return build_instantly_operation_catalog()
    seen: set[str] = set()
    selected: list[InstantlyOperation] = []
    for name in allowed:
        op = get_instantly_operation(name)
        if op.name not in seen:
            seen.add(op.name)
            selected.append(op)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: RequestPreparingClient | None) -> RequestPreparingClient:
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Instantly credentials or an Instantly client must be provided.")
    from harnessiq.providers.instantly.client import InstantlyClient
    return InstantlyClient(credentials=credentials)


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(f"Unsupported Instantly operation '{value}'. Allowed: {allowed_str}.")
    return value


def _optional_mapping(arguments: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    v = arguments.get(key)
    if v is None:
        return None
    if not isinstance(v, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return v


__all__ = [
    "build_instantly_request_tool_definition",
    "create_instantly_tools",
]
