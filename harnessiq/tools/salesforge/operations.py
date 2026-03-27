"""Salesforge MCP-style tool factory for the Harnessiq tool layer."""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from harnessiq.providers.salesforge.operations import (
    SalesforgeOperation,
    build_salesforge_operation_catalog,
    get_salesforge_operation,
)
from harnessiq.shared.dtos import ProviderPayloadRequestDTO
from harnessiq.shared.tools import (
    SALESFORGE_REQUEST,
    RegisteredTool,
    ToolArguments,
    ToolDefinition,
)

if TYPE_CHECKING:
    from harnessiq.providers.salesforge.client import SalesforgeClient
    from harnessiq.providers.salesforge.credentials import SalesforgeCredentials


def build_salesforge_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the Salesforge request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [op.name for op in operations]
    return ToolDefinition(
        key=SALESFORGE_REQUEST,
        name="salesforge_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": (
                        "The Salesforge operation to execute. Sequence operations manage "
                        "email drip cadences and their lifecycle. Sequence Contact operations "
                        "enroll or remove contacts from sequences. Contact operations manage "
                        "the contact database. Mailbox operations inspect sending accounts. "
                        "Unsubscribe operations manage the global opt-out list."
                    ),
                },
                "payload": {
                    "type": "object",
                    "description": (
                        "Parameters for the operation. For create_sequence: "
                        "{name, mailbox_id, daily_limit?, timezone?}. "
                        "For get_sequence / update_sequence / delete_sequence / "
                        "pause_sequence / resume_sequence / get_sequence_stats: {sequence_id}. "
                        "For add_contacts_to_sequence: {sequence_id, contacts: [{...}, ...]}. "
                        "For list_sequence_contacts / remove_contact_from_sequence: "
                        "{sequence_id, contact_id?}. "
                        "For create_contact: {first_name, last_name, email, ...}. "
                        "For get_contact / update_contact / delete_contact / "
                        "get_contact_activity: {contact_id}. "
                        "For get_mailbox: {mailbox_id}. "
                        "For add_unsubscribe / remove_unsubscribe: {email}. "
                        "Omit for list operations that need no parameters."
                    ),
                    "additionalProperties": True,
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_salesforge_tools(
    *,
    credentials: "SalesforgeCredentials | None" = None,
    client: "SalesforgeClient | None" = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the Salesforge request tool backed by the provided client."""
    salesforge_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(op.name for op in selected)
    definition = build_salesforge_request_tool_definition(
        allowed_operations=tuple(op.name for op in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        request = ProviderPayloadRequestDTO(
            operation=_require_operation_name(arguments, allowed_names),
            payload=dict(_optional_mapping(arguments, "payload") or {}),
        )
        return salesforge_client.execute_operation(request).to_dict()

    return (RegisteredTool(definition=definition, handler=handler),)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_tool_description(operations: Sequence[SalesforgeOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())

    lines = [
        "Execute authenticated Salesforge cold email automation API operations.",
        "",
        "Salesforge is an AI-powered cold email platform for outbound sales teams. "
        "Use sequence operations to create and manage multi-step email cadences, "
        "control their execution (pause/resume), and monitor engagement stats. "
        "Contact operations manage the prospect database — create, update, and "
        "organise contacts. Enroll contacts into sequences and remove them when "
        "they convert or opt out. Mailbox operations inspect the sending accounts "
        "used for outreach. The unsubscribe list provides global opt-out management.",
        "",
        "Available operations by category:",
    ]
    for category, summaries in grouped.items():
        lines.append(f"  {category}: {', '.join(summaries)}")
    lines.append(
        "\nParameter guidance: pass all operation-specific arguments inside 'payload' "
        "as key-value pairs. IDs such as sequence_id and contact_id are strings or integers."
    )
    return "\n".join(lines)


def _select_operations(allowed: Sequence[str] | None) -> tuple[SalesforgeOperation, ...]:
    if allowed is None:
        return build_salesforge_operation_catalog()
    seen: set[str] = set()
    selected: list[SalesforgeOperation] = []
    for name in allowed:
        op = get_salesforge_operation(name)
        if op.name not in seen:
            seen.add(op.name)
            selected.append(op)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: Any) -> Any:
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Salesforge credentials or a Salesforge client must be provided.")
    from harnessiq.providers.salesforge.client import SalesforgeClient
    return SalesforgeClient(api_key=credentials["api_key"])


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(f"Unsupported Salesforge operation '{value}'. Allowed: {allowed_str}.")
    return value


def _optional_mapping(
    arguments: Mapping[str, object], key: str
) -> Mapping[str, object] | None:
    v = arguments.get(key)
    if v is None:
        return None
    if not isinstance(v, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return v


__all__ = [
    "build_salesforge_request_tool_definition",
    "create_salesforge_tools",
]
