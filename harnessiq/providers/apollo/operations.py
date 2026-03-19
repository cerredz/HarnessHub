"""Apollo.io operation catalog, tool definition, and MCP-style tool factory."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Mapping, Sequence
from urllib.parse import quote

from harnessiq.providers.http import join_url
from harnessiq.shared.tools import RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.apollo.client import ApolloCredentials

APOLLO_REQUEST = "apollo.request"
PayloadKind = Literal["none", "object"]


@dataclass(frozen=True, slots=True)
class ApolloOperation:
    """Declarative metadata for one Apollo.io API operation."""

    name: str
    category: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path_hint: str
    required_path_params: tuple[str, ...] = ()
    payload_kind: PayloadKind = "none"
    payload_required: bool = False
    allow_query: bool = False

    def summary(self) -> str:
        return f"{self.name} ({self.method} {self.path_hint})"


@dataclass(frozen=True, slots=True)
class ApolloPreparedRequest:
    """A validated Apollo.io request ready for execution."""

    operation: ApolloOperation
    method: str
    path: str
    url: str
    headers: dict[str, str]
    json_body: Any | None


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

def _op(
    name: str,
    category: str,
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
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
        # People — Apollo database (contact intelligence)
        _op("search_people", "People", "POST", "/mixed_people/api_search", payload_kind="object", payload_required=True),
        _op("enrich_person", "People", "POST", "/people/match", payload_kind="object", payload_required=True),
        _op("bulk_enrich_people", "People", "POST", "/people/bulk_match", payload_kind="object", payload_required=True),

        # Contacts — CRM records
        _op("search_contacts", "Contacts", "POST", "/contacts/search", payload_kind="object", payload_required=True),
        _op("create_contact", "Contacts", "POST", "/contacts", payload_kind="object", payload_required=True),
        _op("update_contact", "Contacts", "PATCH", "/contacts/{contact_id}", required_path_params=("contact_id",), payload_kind="object", payload_required=True),

        # Organizations — Apollo database
        _op("search_organizations", "Organizations", "POST", "/mixed_companies/search", payload_kind="object", payload_required=True),
        _op("enrich_organization", "Organizations", "GET", "/organizations/enrich", allow_query=True),

        # Accounts — CRM records
        _op("search_accounts", "Accounts", "POST", "/accounts/search", payload_kind="object", payload_required=True),
        _op("bulk_create_accounts", "Accounts", "POST", "/accounts/bulk_create", payload_kind="object", payload_required=True),
        _op("update_account", "Accounts", "PATCH", "/accounts/{account_id}", required_path_params=("account_id",), payload_kind="object", payload_required=True),

        # Sequences (emailer campaigns)
        _op("search_sequences", "Sequences", "POST", "/emailer_campaigns/search", payload_kind="object", payload_required=True),
        _op("add_contacts_to_sequence", "Sequences", "POST", "/emailer_campaigns/{sequence_id}/add_contact_ids", required_path_params=("sequence_id",), payload_kind="object", payload_required=True),
        _op("remove_contacts_from_sequence", "Sequences", "POST", "/emailer_campaigns/remove_or_stop_contact_ids", payload_kind="object", payload_required=True),

        # Email Accounts
        _op("list_email_accounts", "Email Accounts", "GET", "/email_accounts"),

        # Deals / Opportunities
        _op("search_deals", "Deals", "GET", "/opportunities/search", allow_query=True),
        _op("create_deal", "Deals", "POST", "/opportunities", payload_kind="object", payload_required=True),
        _op("update_deal", "Deals", "PATCH", "/opportunities/{opportunity_id}", required_path_params=("opportunity_id",), payload_kind="object", payload_required=True),

        # Tasks
        _op("search_tasks", "Tasks", "POST", "/tasks/search", payload_kind="object", payload_required=True),
        _op("bulk_create_tasks", "Tasks", "POST", "/tasks/bulk_create", payload_kind="object", payload_required=True),

        # Calls
        _op("search_calls", "Calls", "POST", "/phone_calls/search", payload_kind="object", payload_required=True),
        _op("create_call", "Calls", "POST", "/phone_calls", payload_kind="object", payload_required=True),
        _op("update_call", "Calls", "PUT", "/phone_calls/{call_id}", required_path_params=("call_id",), payload_kind="object", payload_required=True),

        # Admin
        _op("list_users", "Admin", "GET", "/users/search", allow_query=True),
        _op("get_api_usage", "Admin", "POST", "/usage_stats/api_usage_stats", payload_kind="object"),
    )
)


def build_apollo_operation_catalog() -> tuple[ApolloOperation, ...]:
    """Return the supported Apollo.io operation catalog in stable order."""
    return tuple(_APOLLO_CATALOG.values())


def get_apollo_operation(operation_name: str) -> ApolloOperation:
    """Return a supported Apollo.io operation or raise a clear error."""
    op = _APOLLO_CATALOG.get(operation_name)
    if op is None:
        available = ", ".join(_APOLLO_CATALOG)
        raise ValueError(
            f"Unsupported Apollo.io operation '{operation_name}'. Available: {available}."
        )
    return op


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
                    "description": "Apollo.io operation name.",
                },
                "path_params": {
                    "type": "object",
                    "description": "Path parameters such as contact_id, account_id, sequence_id, opportunity_id, call_id.",
                    "additionalProperties": True,
                },
                "query": {
                    "type": "object",
                    "description": "Optional query parameters for GET operations such as enrich_organization and search_deals.",
                    "additionalProperties": True,
                },
                "payload": {
                    "type": "object",
                    "description": "JSON body for search, enrich, create, and update operations.",
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

def _build_prepared_request(
    *,
    operation_name: str,
    credentials: "ApolloCredentials",
    path_params: Mapping[str, object] | None,
    query: Mapping[str, object] | None,
    payload: Any | None,
) -> ApolloPreparedRequest:
    from harnessiq.providers.apollo.api import build_headers

    op = get_apollo_operation(operation_name)
    normalized_params = {str(k): str(v) for k, v in (path_params or {}).items()}
    missing = [k for k in op.required_path_params if not normalized_params.get(k)]
    if missing:
        raise ValueError(
            f"Operation '{op.name}' requires path parameters: {', '.join(missing)}."
        )

    if op.payload_kind == "none" and payload is not None:
        raise ValueError(f"Operation '{op.name}' does not accept a payload.")
    if op.payload_required and payload is None:
        raise ValueError(f"Operation '{op.name}' requires a payload.")

    path = op.path_hint
    for key, value in normalized_params.items():
        path = path.replace(f"{{{key}}}", quote(value, safe=""))

    normalized_query = {str(k): v for k, v in query.items()} if query else None
    full_url = join_url(credentials.base_url, path, query=normalized_query)  # type: ignore[arg-type]
    headers = build_headers(credentials.api_key)

    return ApolloPreparedRequest(
        operation=op,
        method=op.method,
        path=path,
        url=full_url,
        headers=headers,
        json_body=deepcopy(payload) if payload is not None else None,
    )


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
        allowed_str = ", ".join(sorted(allowed))
        raise ValueError(f"Unsupported Apollo.io operation '{value}'. Allowed: {allowed_str}.")
    return value


def _optional_mapping(arguments: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    v = arguments.get(key)
    if v is None:
        return None
    if not isinstance(v, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return v


def _build_tool_description(operations: Sequence[ApolloOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())
    lines = ["Execute authenticated Apollo.io sales intelligence API operations."]
    for category, summaries in grouped.items():
        lines.append(f"{category}: {', '.join(summaries)}")
    lines.append(
        "Use 'path_params' for resource ids, 'query' for GET filter operations, "
        "'payload' for search/enrich/create/update JSON bodies."
    )
    return "\n".join(lines)


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
