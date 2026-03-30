"""
===============================================================================
File: harnessiq/tools/leadiq/operations.py

What this file does:
- Exposes the `leadiq` tool family for the HarnessIQ tool layer.
- In most packages this module is the bridge between provider-backed operations
  and the generic tool registration surface.
- LeadIQ MCP-style tool factory for the Harnessiq tool layer.

Use cases:
- Import this module when an agent or registry needs the `leadiq` tool
  definitions.
- Read it to see which runtime operations are intentionally surfaced as tools.

How to use it:
- Call the exported factory helpers from `harnessiq/tools/leadiq` and merge the
  resulting tools into a registry.

Intent:
- Keep the public `leadiq` tool surface small, explicit, and separate from
  provider implementation details.
===============================================================================
"""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from harnessiq.providers.leadiq.operations import (
    LeadIQOperation,
    build_leadiq_operation_catalog,
    get_leadiq_operation,
)
from harnessiq.shared.dtos import ProviderPayloadRequestDTO
from harnessiq.shared.tools import LEADIQ_REQUEST, RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.leadiq.client import LeadIQClient
    from harnessiq.providers.leadiq.credentials import LeadIQCredentials


def build_leadiq_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the LeadIQ request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [op.name for op in operations]
    return ToolDefinition(
        key=LEADIQ_REQUEST,
        name="leadiq_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": (
                        "The LeadIQ operation to execute. Contact operations search, enrich, "
                        "and look up B2B contacts. Company operations search organisations. "
                        "Lead capture operations batch-import contacts and check import status. "
                        "Tag operations organise contacts within the workspace."
                    ),
                },
                "payload": {
                    "type": "object",
                    "description": (
                        "Parameters for the operation. For search_contacts: "
                        "{name?, email?, company?, title?, location?, linkedin_url?, page?, per_page?}. "
                        "For find_person_by_linkedin: {linkedin_url}. "
                        "For enrich_contact / get_contact_details / get_capture_status: {contact_id}. "
                        "For capture_leads: {contacts: [{...}, ...]}. "
                        "For add_tag_to_contact / remove_tag_from_contact: {contact_id, tag_id}. "
                        "Omit for operations that need no parameters (e.g., get_tags)."
                    ),
                    "additionalProperties": True,
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_leadiq_tools(
    *,
    credentials: "LeadIQCredentials | None" = None,
    client: "LeadIQClient | None" = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the LeadIQ request tool backed by the provided client."""
    leadiq_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(op.name for op in selected)
    definition = build_leadiq_request_tool_definition(
        allowed_operations=tuple(op.name for op in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        request = ProviderPayloadRequestDTO(
            operation=_require_operation_name(arguments, allowed_names),
            payload=dict(_optional_mapping(arguments, "payload") or {}),
        )
        return leadiq_client.execute_operation(request).to_dict()

    return (RegisteredTool(definition=definition, handler=handler),)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_tool_description(operations: Sequence[LeadIQOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())

    lines = [
        "Execute authenticated LeadIQ B2B contact intelligence API operations.",
        "",
        "LeadIQ is a sales intelligence platform that surfaces verified contact data "
        "for B2B prospecting. Use search_contacts and search_companies to discover "
        "prospects by firmographic and personal attributes. Use find_person_by_linkedin "
        "or enrich_contact to surface verified emails and phone numbers. Capture leads "
        "in bulk with capture_leads and monitor import status with get_capture_status. "
        "All operations communicate through LeadIQ's GraphQL API authenticated with "
        "an API key.",
        "",
        "Available operations by category:",
    ]
    for category, summaries in grouped.items():
        lines.append(f"  {category}: {', '.join(summaries)}")
    lines.append(
        "\nParameter guidance: pass all operation-specific arguments inside 'payload' "
        "as key-value pairs. Optional parameters can be omitted from the payload."
    )
    return "\n".join(lines)


def _select_operations(allowed: Sequence[str] | None) -> tuple[LeadIQOperation, ...]:
    if allowed is None:
        return build_leadiq_operation_catalog()
    seen: set[str] = set()
    selected: list[LeadIQOperation] = []
    for name in allowed:
        op = get_leadiq_operation(name)
        if op.name not in seen:
            seen.add(op.name)
            selected.append(op)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: Any) -> Any:
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either LeadIQ credentials or a LeadIQ client must be provided.")
    from harnessiq.providers.leadiq.client import LeadIQClient
    return LeadIQClient(api_key=credentials["api_key"])


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(f"Unsupported LeadIQ operation '{value}'. Allowed: {allowed_str}.")
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
    "build_leadiq_request_tool_definition",
    "create_leadiq_tools",
]
