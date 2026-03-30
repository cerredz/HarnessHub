"""
===============================================================================
File: harnessiq/tools/lusha/operations.py

What this file does:
- Exposes the `lusha` tool family for the HarnessIQ tool layer.
- In most packages this module is the bridge between provider-backed operations
  and the generic tool registration surface.
- Lusha MCP-style tool factory for the Harnessiq tool layer.

Use cases:
- Import this module when an agent or registry needs the `lusha` tool
  definitions.
- Read it to see which runtime operations are intentionally surfaced as tools.

How to use it:
- Call the exported factory helpers from `harnessiq/tools/lusha` and merge the
  resulting tools into a registry.

Intent:
- Keep the public `lusha` tool surface small, explicit, and separate from
  provider implementation details.
===============================================================================
"""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from harnessiq.interfaces import RequestPreparingClient
from harnessiq.shared.dtos import ProviderOperationRequestDTO

from harnessiq.providers.lusha.operations import (
    LushaOperation,
    build_lusha_operation_catalog,
    get_lusha_operation,
)
from harnessiq.shared.tools import LUSHA_REQUEST, RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.lusha.client import LushaClient, LushaCredentials


def build_lusha_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the Lusha request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [op.name for op in operations]
    return ToolDefinition(
        key=LUSHA_REQUEST,
        name="lusha_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": (
                        "The Lusha operation to execute. Use 'enrich_person' to find contact "
                        "details (email, phone) by name + company, email, or LinkedIn URL. "
                        "Use 'search_contacts' + 'enrich_contacts' for prospecting (search is free, "
                        "enrich charges credits). Use 'find_similar_contacts' to discover lookalike "
                        "prospects using AI. Use 'get_contact_signals' to track job changes and "
                        "promotions. Use 'create_subscriptions' to subscribe to signal webhooks "
                        "for real-time alerts."
                    ),
                },
                "path_params": {
                    "type": "object",
                    "description": (
                        "Path parameters for resource operations. "
                        "get_signal_filters: {object_type: 'contact'|'company'}. "
                        "get_subscription / update_subscription / test_subscription / delete_subscriptions: "
                        "{subscription_id}."
                    ),
                    "additionalProperties": True,
                },
                "query": {
                    "type": "object",
                    "description": (
                        "Query parameters for GET enrichment and list operations. "
                        "enrich_person: {firstName, lastName, companyName or companyDomain, or email, "
                        "or linkedinUrl; revealEmails (bool), revealPhones (bool)}. "
                        "enrich_company: {domain or company}. "
                        "list_subscriptions: {page (opt)}."
                    ),
                    "additionalProperties": True,
                },
                "payload": {
                    "type": "object",
                    "description": (
                        "JSON body for POST/PATCH operations. "
                        "search_contacts: {include: {departments, seniority, locations, company, signals}, "
                        "exclude: {...}, excludeDnc (bool)}. "
                        "enrich_contacts: {contactIds: [id1, id2, ...]} (up to 100). "
                        "bulk_enrich_persons: array of person objects (up to 100). "
                        "get_contact_signals: {contactIds: [...]}. "
                        "create_subscriptions: array of subscription objects (up to 25). "
                        "find_similar_contacts: {contacts: [...], dedupeSessionId (opt)}."
                    ),
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_lusha_tools(
    *,
    credentials: "LushaCredentials | None" = None,
    client: RequestPreparingClient | None = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the MCP-style Lusha request tool backed by the provided client."""
    lusha_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(op.name for op in selected)
    definition = build_lusha_request_tool_definition(
        allowed_operations=tuple(op.name for op in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        request = ProviderOperationRequestDTO(
            operation=_require_operation_name(arguments, allowed_names),
            path_params=_optional_mapping(arguments, "path_params") or {},
            query=_optional_mapping(arguments, "query") or {},
            payload=arguments.get("payload"),
        )
        return lusha_client.execute_operation(request).to_dict()

    return (RegisteredTool(definition=definition, handler=handler),)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_tool_description(operations: Sequence[LushaOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())

    lines = [
        "Execute authenticated Lusha B2B contact and company intelligence API operations.",
        "",
        "Lusha provides accurate contact data (work email, direct phone, mobile) and company "
        "intelligence for 100M+ professionals. Use it to enrich contacts individually or in bulk "
        "(up to 100 per request), build targeted prospect lists using advanced filters (department, "
        "seniority, company size, industry, intent, technology), discover lookalike prospects with "
        "AI, track buying signals (job changes, hiring surges, company growth), and subscribe to "
        "real-time webhook notifications. Credits are charged at the enrich step, not the search step.",
        "",
        "Available operations by category:",
    ]
    for category, summaries in grouped.items():
        lines.append(f"  {category}: {', '.join(summaries)}")
    lines.append(
        "\nParameter guidance: Use 'query' for GET enrichment lookups (enrich_person, enrich_company). "
        "Use 'payload' for bulk arrays, prospecting search filters, signal queries, and webhook configs. "
        "Use 'path_params' for object_type (signals) and subscription_id (webhook management)."
    )
    return "\n".join(lines)


def _select_operations(allowed: Sequence[str] | None) -> tuple[LushaOperation, ...]:
    if allowed is None:
        return build_lusha_operation_catalog()
    seen: set[str] = set()
    selected: list[LushaOperation] = []
    for name in allowed:
        op = get_lusha_operation(name)
        if op.name not in seen:
            seen.add(op.name)
            selected.append(op)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: RequestPreparingClient | None) -> RequestPreparingClient:
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Lusha credentials or a Lusha client must be provided.")
    from harnessiq.providers.lusha.client import LushaClient
    return LushaClient(credentials=credentials)


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(
            f"Unsupported Lusha operation '{value}'. Allowed: {allowed_str}."
        )
    return value


def _optional_mapping(arguments: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    v = arguments.get(key)
    if v is None:
        return None
    if not isinstance(v, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return v


__all__ = [
    "build_lusha_request_tool_definition",
    "create_lusha_tools",
]
