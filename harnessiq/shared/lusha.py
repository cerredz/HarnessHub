"""Lusha operation catalog, tool definition, and MCP-style tool factory."""

from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Literal, Sequence

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

__all__ = [
    "LushaOperation",
    "LushaPreparedRequest",
    "build_lusha_operation_catalog",
    "get_lusha_operation",
]
