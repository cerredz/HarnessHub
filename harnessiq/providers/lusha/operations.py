"""Lusha operation catalog, tool definition, and MCP-style tool factory."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Mapping, Sequence
from urllib.parse import quote

from harnessiq.providers.http import join_url
from harnessiq.shared.tools import RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.lusha.client import LushaCredentials

LUSHA_REQUEST = "lusha.request"
PayloadKind = Literal["none", "object"]


@dataclass(frozen=True, slots=True)
class LushaOperation:
    """Declarative metadata for one Lusha API operation."""

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
class LushaPreparedRequest:
    """A validated Lusha request ready for execution."""

    operation: LushaOperation
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
) -> tuple[str, LushaOperation]:
    return (
        name,
        LushaOperation(
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


_LUSHA_CATALOG: OrderedDict[str, LushaOperation] = OrderedDict(
    (
        # Person Enrichment
        _op("enrich_person", "Person Enrichment", "GET", "/v2/person", allow_query=True),
        _op("bulk_enrich_persons", "Person Enrichment", "POST", "/v2/person", payload_kind="object", payload_required=True),

        # Company Enrichment
        _op("enrich_company", "Company Enrichment", "GET", "/v2/company", allow_query=True),
        _op("bulk_enrich_companies", "Company Enrichment", "POST", "/bulk/company/v2", payload_kind="object", payload_required=True),

        # Prospecting — Contact Search & Enrich
        _op("search_contacts", "Prospecting", "POST", "/prospecting/contact/search", payload_kind="object", payload_required=True),
        _op("enrich_contacts", "Prospecting", "POST", "/prospecting/contact/enrich", payload_kind="object", payload_required=True),

        # Prospecting — Company Search & Enrich
        _op("search_companies", "Prospecting", "POST", "/prospecting/company/search", payload_kind="object", payload_required=True),
        _op("enrich_companies", "Prospecting", "POST", "/prospecting/company/enrich", payload_kind="object", payload_required=True),

        # Contact Filters
        _op("get_contact_departments", "Contact Filters", "GET", "/prospecting/filters/contacts/departments"),
        _op("get_contact_seniority_levels", "Contact Filters", "GET", "/prospecting/filters/contacts/seniority"),
        _op("get_contact_data_points", "Contact Filters", "GET", "/prospecting/filters/contacts/existing_data_points"),
        _op("get_all_countries", "Contact Filters", "GET", "/prospecting/filters/contacts/all_countries"),
        _op("search_contact_locations", "Contact Filters", "POST", "/prospecting/filters/contacts/locations", payload_kind="object", payload_required=True),

        # Company Filters
        _op("search_company_names", "Company Filters", "POST", "/prospecting/filters/companies/names", payload_kind="object", payload_required=True),
        _op("get_industry_labels", "Company Filters", "GET", "/prospecting/filters/companies/industries_labels"),
        _op("get_company_sizes", "Company Filters", "GET", "/prospecting/filters/companies/sizes"),
        _op("get_company_revenues", "Company Filters", "GET", "/prospecting/filters/companies/revenues"),
        _op("search_company_locations", "Company Filters", "POST", "/prospecting/filters/companies/locations", payload_kind="object", payload_required=True),
        _op("get_sic_codes", "Company Filters", "GET", "/prospecting/filters/companies/sics"),
        _op("get_naics_codes", "Company Filters", "GET", "/prospecting/filters/companies/naics"),
        _op("get_intent_topics", "Company Filters", "GET", "/prospecting/filters/companies/intent_topics"),
        _op("search_technologies", "Company Filters", "POST", "/prospecting/filters/companies/technologies", payload_kind="object", payload_required=True),

        # Signals
        _op("get_signal_filters", "Signals", "GET", "/api/signals/filters/{object_type}", required_path_params=("object_type",)),
        _op("get_contact_signals", "Signals", "POST", "/api/signals/contacts", payload_kind="object", payload_required=True),
        _op("search_contact_signals", "Signals", "POST", "/api/signals/contacts/search", payload_kind="object", payload_required=True),
        _op("get_company_signals", "Signals", "POST", "/api/signals/companies", payload_kind="object", payload_required=True),
        _op("search_company_signals", "Signals", "POST", "/api/signals/companies/search", payload_kind="object", payload_required=True),

        # Lookalikes
        _op("find_similar_contacts", "Lookalikes", "POST", "/v3/lookalike/contacts", payload_kind="object", payload_required=True),
        _op("find_similar_companies", "Lookalikes", "POST", "/v3/lookalike/companies", payload_kind="object", payload_required=True),

        # Webhooks / Subscriptions
        _op("create_subscriptions", "Webhooks", "POST", "/api/subscriptions", payload_kind="object", payload_required=True),
        _op("list_subscriptions", "Webhooks", "GET", "/api/subscriptions", allow_query=True),
        _op("get_subscription", "Webhooks", "GET", "/api/subscriptions/{subscription_id}", required_path_params=("subscription_id",)),
        _op("update_subscription", "Webhooks", "PATCH", "/api/subscriptions/{subscription_id}", required_path_params=("subscription_id",), payload_kind="object", payload_required=True),
        _op("delete_subscriptions", "Webhooks", "POST", "/api/subscriptions/delete", payload_kind="object", payload_required=True),
        _op("test_subscription", "Webhooks", "POST", "/api/subscriptions/{subscription_id}/test", required_path_params=("subscription_id",), payload_kind="object"),
        _op("get_webhook_audit_logs", "Webhooks", "GET", "/api/audit-logs", allow_query=True),
        _op("get_webhook_audit_stats", "Webhooks", "GET", "/api/audit-logs/stats"),
        _op("get_webhook_secret", "Webhooks", "GET", "/api/account/secret"),
        _op("regenerate_webhook_secret", "Webhooks", "POST", "/api/account/secret/regenerate"),

        # Account
        _op("get_account_usage", "Account", "GET", "/account/usage"),
    )
)


def build_lusha_operation_catalog() -> tuple[LushaOperation, ...]:
    """Return the supported Lusha operation catalog in stable order."""
    return tuple(_LUSHA_CATALOG.values())


def get_lusha_operation(operation_name: str) -> LushaOperation:
    """Return a supported Lusha operation or raise a clear error."""
    op = _LUSHA_CATALOG.get(operation_name)
    if op is None:
        available = ", ".join(_LUSHA_CATALOG)
        raise ValueError(
            f"Unsupported Lusha operation '{operation_name}'. Available: {available}."
        )
    return op


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
                    "description": "Lusha operation name.",
                },
                "path_params": {
                    "type": "object",
                    "description": "Path parameters such as object_type (for get_signal_filters) and subscription_id.",
                    "additionalProperties": True,
                },
                "query": {
                    "type": "object",
                    "description": (
                        "Query parameters for GET enrichment operations. "
                        "enrich_person: firstName, lastName, companyName/companyDomain, or email or linkedinUrl. "
                        "enrich_company: domain or company. "
                        "get_account_usage: (none required)."
                    ),
                    "additionalProperties": True,
                },
                "payload": {
                    "type": "object",
                    "description": "JSON body for POST/PATCH operations (bulk arrays, search filters, subscription config).",
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_lusha_tools(
    *,
    credentials: "LushaCredentials | None" = None,
    client: "Any | None" = None,
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
        operation_name = _require_operation_name(arguments, allowed_names)
        prepared = lusha_client.prepare_request(
            operation_name,
            path_params=_optional_mapping(arguments, "path_params"),
            query=_optional_mapping(arguments, "query"),
            payload=arguments.get("payload"),
        )
        response = lusha_client.request_executor(
            prepared.method,
            prepared.url,
            headers=prepared.headers,
            json_body=prepared.json_body,
            timeout_seconds=lusha_client.credentials.timeout_seconds,
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
    credentials: "LushaCredentials",
    path_params: Mapping[str, object] | None,
    query: Mapping[str, object] | None,
    payload: Any | None,
) -> LushaPreparedRequest:
    from harnessiq.providers.lusha.api import build_headers

    op = get_lusha_operation(operation_name)
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

    return LushaPreparedRequest(
        operation=op,
        method=op.method,
        path=path,
        url=full_url,
        headers=headers,
        json_body=deepcopy(payload) if payload is not None else None,
    )


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


def _coerce_client(*, credentials: Any, client: Any) -> Any:
    from harnessiq.providers.lusha.client import LushaClient
    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Lusha credentials or a Lusha client must be provided.")
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


def _build_tool_description(operations: Sequence[LushaOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())
    lines = ["Execute authenticated Lusha B2B contact and company intelligence API operations."]
    for category, summaries in grouped.items():
        lines.append(f"{category}: {', '.join(summaries)}")
    lines.append(
        "Use 'query' for GET enrichment lookups. 'path_params' for object_type and subscription_id. "
        "'payload' for bulk arrays, search filters, and webhook configs."
    )
    return "\n".join(lines)


__all__ = [
    "LUSHA_REQUEST",
    "LushaOperation",
    "LushaPreparedRequest",
    "_build_prepared_request",
    "build_lusha_operation_catalog",
    "build_lusha_request_tool_definition",
    "create_lusha_tools",
    "get_lusha_operation",
]
