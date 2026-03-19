"""Apollo operation catalog, tool definition, and request preparation."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Mapping, Sequence
from urllib.parse import quote

from harnessiq.providers.apollo.api import build_headers, url
from harnessiq.providers.apollo.requests import (
    build_add_contacts_to_sequence_request,
    build_bulk_enrich_organizations_request,
    build_bulk_enrich_people_request,
    build_create_contact_request,
    build_enrich_organization_query,
    build_enrich_person_request,
    build_search_contacts_request,
    build_search_organizations_request,
    build_search_people_request,
    build_search_sequences_request,
    build_update_contact_request,
    build_usage_stats_request,
)
from harnessiq.shared.tools import RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.apollo.credentials import ApolloCredentials

APOLLO_REQUEST = "apollo.request"
PayloadKind = Literal["none", "object"]


@dataclass(frozen=True, slots=True)
class ApolloOperation:
    """Declarative metadata for one Apollo API operation."""

    name: str
    category: str
    method: Literal["GET", "POST", "PATCH"]
    path_hint: str
    required_path_params: tuple[str, ...] = ()
    payload_kind: PayloadKind = "none"
    payload_required: bool = False
    allow_query: bool = False

    def summary(self) -> str:
        return f"{self.name} ({self.method} {self.path_hint})"


@dataclass(frozen=True, slots=True)
class ApolloPreparedRequest:
    """A validated Apollo request ready for execution."""

    operation: ApolloOperation
    method: str
    path: str
    url: str
    headers: dict[str, str]
    json_body: Any | None


def _op(
    name: str,
    category: str,
    method: Literal["GET", "POST", "PATCH"],
    path_hint: str,
    *,
    required_path_params: Sequence[str] = (),
    payload_kind: PayloadKind = "none",
    payload_required: bool = False,
    allow_query: bool = False,
) -> tuple[str, ApolloOperation]:
    return (
        name,
        ApolloOperation(
            name=name,
            category=category,
            method=method,
            path_hint=path_hint,
            required_path_params=tuple(required_path_params),
            payload_kind=payload_kind,
            payload_required=payload_required,
            allow_query=allow_query,
        ),
    )


_APOLLO_CATALOG: OrderedDict[str, ApolloOperation] = OrderedDict(
    (
        _op("search_people", "Search", "POST", "/mixed_people/api_search", payload_kind="object", payload_required=True),
        _op("search_organizations", "Search", "POST", "/mixed_companies/search", payload_kind="object", payload_required=True),
        _op("enrich_person", "Enrichment", "POST", "/people/match", payload_kind="object", payload_required=True),
        _op("bulk_enrich_people", "Enrichment", "POST", "/people/bulk_match", payload_kind="object", payload_required=True),
        _op("enrich_organization", "Enrichment", "GET", "/organizations/enrich", allow_query=True),
        _op("bulk_enrich_organizations", "Enrichment", "POST", "/organizations/bulk_enrich", payload_kind="object", payload_required=True),
        _op("create_contact", "Contact", "POST", "/contacts", payload_kind="object", payload_required=True, allow_query=True),
        _op("search_contacts", "Contact", "POST", "/contacts/search", payload_kind="object"),
        _op("view_contact", "Contact", "GET", "/contacts/{contact_id}", required_path_params=("contact_id",)),
        _op("update_contact", "Contact", "PATCH", "/contacts/{contact_id}", required_path_params=("contact_id",), payload_kind="object", payload_required=True, allow_query=True),
        _op("search_sequences", "Sequence", "POST", "/emailer_campaigns/search", payload_kind="object"),
        _op("add_contacts_to_sequence", "Sequence", "POST", "/emailer_campaigns/{sequence_id}/add_contact_ids", required_path_params=("sequence_id",), payload_kind="object", payload_required=True),
        _op("view_usage_stats", "Utility", "POST", "/usage_stats/api_usage_stats", payload_kind="object"),
    )
)


def build_apollo_operation_catalog() -> tuple[ApolloOperation, ...]:
    """Return the supported Apollo operation catalog in stable order."""
    return tuple(_APOLLO_CATALOG.values())


def get_apollo_operation(operation_name: str) -> ApolloOperation:
    """Return a supported Apollo operation or raise a clear error."""
    operation = _APOLLO_CATALOG.get(operation_name)
    if operation is None:
        available = ", ".join(_APOLLO_CATALOG)
        raise ValueError(f"Unsupported Apollo operation '{operation_name}'. Available: {available}.")
    return operation


def build_apollo_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the Apollo request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [operation.name for operation in operations]
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
                    "description": "Apollo operation name.",
                },
                "path_params": {
                    "type": "object",
                    "description": "Path parameters such as contact_id or sequence_id.",
                    "additionalProperties": True,
                },
                "query": {
                    "type": "object",
                    "description": "Optional query parameters for GET enrichment or dedupe toggles.",
                    "additionalProperties": True,
                },
                "payload": {
                    "type": "object",
                    "description": "Optional JSON body for search, enrichment, contact, and sequence operations.",
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_apollo_tools(
    *,
    credentials: "ApolloCredentials | None" = None,
    client: "Any | None" = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the MCP-style Apollo request tool backed by the provided client."""
    apollo_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(operation.name for operation in selected)
    definition = build_apollo_request_tool_definition(
        allowed_operations=tuple(operation.name for operation in selected)
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


def _build_prepared_request(
    *,
    operation_name: str,
    credentials: "ApolloCredentials",
    path_params: Mapping[str, object] | None,
    query: Mapping[str, object] | None,
    payload: Any | None,
) -> ApolloPreparedRequest:
    operation = get_apollo_operation(operation_name)
    normalized_params = {str(key): str(value) for key, value in (path_params or {}).items()}
    missing = [key for key in operation.required_path_params if not normalized_params.get(key)]
    if missing:
        raise ValueError(f"Operation '{operation.name}' requires path parameters: {', '.join(missing)}.")

    if operation.payload_kind == "none" and payload is not None:
        raise ValueError(f"Operation '{operation.name}' does not accept a payload.")
    if operation.payload_required and payload is None:
        raise ValueError(f"Operation '{operation.name}' requires a payload.")

    path = operation.path_hint
    for key, value in normalized_params.items():
        path = path.replace(f"{{{key}}}", quote(value, safe=""))

    normalized_query: dict[str, str | int | float | bool] | None = None
    if query is not None:
        if not operation.allow_query:
            raise ValueError(f"Operation '{operation.name}' does not accept query parameters.")
        normalized_query = _normalize_query(operation.name, query)

    return ApolloPreparedRequest(
        operation=operation,
        method=operation.method,
        path=path,
        url=url(credentials.base_url, path, query=normalized_query),
        headers=build_headers(credentials.api_key),
        json_body=_normalize_payload(operation.name, payload),
    )


def _select_operations(allowed: Sequence[str] | None) -> tuple[ApolloOperation, ...]:
    if allowed is None:
        return build_apollo_operation_catalog()
    seen: set[str] = set()
    selected: list[ApolloOperation] = []
    for name in allowed:
        operation = get_apollo_operation(name)
        if operation.name not in seen:
            seen.add(operation.name)
            selected.append(operation)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: Any) -> Any:
    from harnessiq.providers.apollo.client import ApolloClient

    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Apollo credentials or an Apollo client must be provided.")
    return ApolloClient(credentials=credentials)


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        raise ValueError(f"Unsupported Apollo operation '{value}'.")
    return value


def _optional_mapping(arguments: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    value = arguments.get(key)
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return value


def _build_tool_description(operations: Sequence[ApolloOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for operation in operations:
        grouped.setdefault(operation.category, []).append(operation.summary())
    lines = [
        "Execute authenticated Apollo sales intelligence and engagement API operations.",
        "",
        "Use people and organization search for prospect discovery, enrichment operations for shortlist enrichment, contact operations for Apollo-native persistence, sequence operations for campaign handoff, and usage stats for budget introspection.",
    ]
    for category, summaries in grouped.items():
        lines.append(f"{category}: {', '.join(summaries)}")
    lines.append("Use 'path_params' for resource ids, 'query' for GET enrichment and dedupe toggles, and 'payload' for JSON request bodies.")
    return "\n".join(lines)


def _normalize_payload(operation_name: str, payload: Any | None) -> Any | None:
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise ValueError(f"Operation '{operation_name}' requires an object payload.")

    builders = {
        "search_people": build_search_people_request,
        "search_organizations": build_search_organizations_request,
        "enrich_person": build_enrich_person_request,
        "bulk_enrich_people": build_bulk_enrich_people_request,
        "bulk_enrich_organizations": build_bulk_enrich_organizations_request,
        "create_contact": build_create_contact_request,
        "search_contacts": build_search_contacts_request,
        "update_contact": build_update_contact_request,
        "search_sequences": build_search_sequences_request,
        "add_contacts_to_sequence": build_add_contacts_to_sequence_request,
        "view_usage_stats": build_usage_stats_request,
    }
    builder = builders.get(operation_name)
    if builder is None:
        return deepcopy(payload)
    return builder(payload)


def _normalize_query(
    operation_name: str,
    query: Mapping[str, object],
) -> dict[str, str | int | float | bool]:
    normalized = dict(query)
    if operation_name == "enrich_organization":
        return build_enrich_organization_query(normalized)
    return {str(key): value for key, value in normalized.items()}


__all__ = [
    "APOLLO_REQUEST",
    "ApolloOperation",
    "ApolloPreparedRequest",
    "_build_prepared_request",
    "build_apollo_operation_catalog",
    "build_apollo_request_tool_definition",
    "create_apollo_tools",
    "get_apollo_operation",
]
