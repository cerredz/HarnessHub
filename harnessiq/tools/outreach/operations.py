"""Outreach MCP-style tool factory for the Harnessiq tool layer."""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from harnessiq.interfaces import RequestPreparingClient
from harnessiq.shared.dtos import ProviderOperationRequestDTO

from harnessiq.providers.outreach.operations import (
    OutreachOperation,
    build_outreach_operation_catalog,
    get_outreach_operation,
)
from harnessiq.shared.tools import OUTREACH_REQUEST, RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.outreach.client import OutreachClient, OutreachCredentials


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
                    "description": (
                        "The Outreach operation to execute. Prospect and account operations "
                        "manage your CRM records. Sequence operations control email/call "
                        "sequences and enrollment. Task and call operations track sales "
                        "activities. Opportunity operations manage pipeline stages."
                    ),
                },
                "path_params": {
                    "type": "object",
                    "description": "Path parameters such as prospect_id, account_id, or sequence_id.",
                    "additionalProperties": True,
                },
                "query": {
                    "type": "object",
                    "description": "Optional query parameters for list and filter operations.",
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


def create_outreach_tools(
    *,
    credentials: "OutreachCredentials | None" = None,
    client: RequestPreparingClient | None = None,
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
        request = ProviderOperationRequestDTO(
            operation=_require_operation_name(arguments, allowed_names),
            path_params=_optional_mapping(arguments, "path_params") or {},
            query=_optional_mapping(arguments, "query") or {},
            payload=arguments.get("payload"),
        )
        return outreach_client.execute_operation(request).to_dict()

    return (RegisteredTool(definition=definition, handler=handler),)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_tool_description(operations: Sequence[OutreachOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())

    lines = [
        "Execute authenticated Outreach B2B sales engagement platform API operations.",
        "",
        "Outreach is an enterprise sales engagement and pipeline management platform. "
        "Use prospect and account operations to manage CRM records. Sequence operations "
        "enroll prospects into email/call cadences and track step completion. Task and "
        "call operations log sales activities. Opportunity operations track pipeline stage "
        "progression. Mailbox operations configure sending identities. Template and snippet "
        "operations manage reusable content.",
        "",
        "Available operations by category:",
    ]
    for category, summaries in grouped.items():
        lines.append(f"  {category}: {', '.join(summaries)}")
    lines.append(
        "\nParameter guidance: 'path_params' for resource ids (prospect_id, sequence_id), "
        "'query' for filters and pagination, 'payload' for JSON-API formatted request bodies."
    )
    return "\n".join(lines)


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


def _coerce_client(*, credentials: Any, client: RequestPreparingClient | None) -> RequestPreparingClient:
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Outreach credentials or an Outreach client must be provided.")
    from harnessiq.providers.outreach.client import OutreachClient
    return OutreachClient(credentials=credentials)


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(f"Unsupported Outreach operation '{value}'. Allowed: {allowed_str}.")
    return value


def _optional_mapping(arguments: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    v = arguments.get(key)
    if v is None:
        return None
    if not isinstance(v, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return v


__all__ = [
    "build_outreach_request_tool_definition",
    "create_outreach_tools",
]
