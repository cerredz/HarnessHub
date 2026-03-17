"""Apollo.io MCP-style tool factory for the Harnessiq tool layer."""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from harnessiq.providers.apollo.operations import (
    ApolloOperation,
    build_apollo_operation_catalog,
    get_apollo_operation,
)
from harnessiq.shared.tools import APOLLO_REQUEST, RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.apollo.client import ApolloClient, ApolloCredentials


def build_apollo_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the Apollo.io request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [op.name for op in operations]
    return ToolDefinition(
        key=APOLLO_REQUEST,
        name="apollo_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": (
                        "The Apollo.io operation to execute. Use 'search_people' or "
                        "'enrich_person' to find and enrich contacts in Apollo's database. "
                        "Use 'search_contacts' / 'create_contact' / 'update_contact' for CRM "
                        "record management. Use 'search_organizations' / 'enrich_organization' "
                        "for company intelligence. Sequence operations manage outreach campaigns. "
                        "Deal, task, and call operations integrate with the Apollo CRM."
                    ),
                },
                "path_params": {
                    "type": "object",
                    "description": (
                        "Path parameters for resource-specific operations. "
                        "Supported keys: contact_id, account_id, sequence_id, "
                        "opportunity_id, call_id."
                    ),
                    "additionalProperties": True,
                },
                "query": {
                    "type": "object",
                    "description": (
                        "Query parameters for GET operations such as 'enrich_organization' "
                        "(domain, organization_name) and 'search_deals'."
                    ),
                    "additionalProperties": True,
                },
                "payload": {
                    "type": "object",
                    "description": (
                        "JSON request body for search, enrich, create, and update operations. "
                        "For 'enrich_person': provide first_name, last_name, organization_name "
                        "or email or linkedin_url. For 'search_people': provide person_titles, "
                        "person_locations, organization_domains filters. For 'add_contacts_to_sequence': "
                        "provide contact_ids array."
                    ),
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_apollo_tools(
    *,
    credentials: "ApolloCredentials | None" = None,
    client: "ApolloClient | None" = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the MCP-style Apollo.io request tool backed by the provided client."""
    apollo_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(op.name for op in selected)
    definition = build_apollo_request_tool_definition(
        allowed_operations=tuple(op.name for op in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        operation_name = _require_operation_name(arguments, allowed_names)
        prepared = apollo_client.prepare_request(
            operation_name,
            path_params=_optional_mapping(arguments, "path_params"),
            query=_optional_mapping(arguments, "query"),
            payload=arguments.get("payload"),
        )
        response = apollo_client.request_executor(
            prepared.method,
            prepared.url,
            headers=prepared.headers,
            json_body=prepared.json_body,
            timeout_seconds=apollo_client.credentials.timeout_seconds,
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

def _build_tool_description(operations: Sequence[ApolloOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())

    lines = [
        "Execute authenticated Apollo.io B2B sales intelligence and engagement API operations.",
        "",
        "Apollo.io is a full-stack sales intelligence platform with a database of 275M+ "
        "contacts and 60M+ companies. Use it to search and enrich leads (people and companies), "
        "manage CRM contacts and accounts, run outreach sequences, track deals and opportunities, "
        "log calls and tasks, and monitor API usage. Ideal for prospecting, contact enrichment, "
        "and CRM data management at scale.",
        "",
        "Available operations by category:",
    ]
    for category, summaries in grouped.items():
        lines.append(f"  {category}: {', '.join(summaries)}")
    lines.append(
        "\nParameter guidance: 'payload' carries the main request body (search filters, "
        "enrich inputs, create/update fields). Use 'path_params' for resource ids "
        "(contact_id, account_id, sequence_id, opportunity_id, call_id). "
        "Use 'query' for GET filter operations (enrich_organization, search_deals, list_users)."
    )
    return "\n".join(lines)


def _select_operations(allowed: Sequence[str] | None) -> tuple[ApolloOperation, ...]:
    if allowed is None:
        return build_apollo_operation_catalog()
    seen: set[str] = set()
    selected: list[ApolloOperation] = []
    for name in allowed:
        op = get_apollo_operation(name)
        if op.name not in seen:
            seen.add(op.name)
            selected.append(op)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: Any) -> Any:
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Apollo credentials or an Apollo client must be provided.")
    from harnessiq.providers.apollo.client import ApolloClient
    return ApolloClient(credentials=credentials)


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(
            f"Unsupported Apollo.io operation '{value}'. Allowed: {allowed_str}."
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
    "build_apollo_request_tool_definition",
    "create_apollo_tools",
]
