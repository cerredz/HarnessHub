"""Apollo operation catalog, tool definition, and request preparation."""

from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Literal, Sequence

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

__all__ = [
    "ApolloOperation",
    "ApolloPreparedRequest",
    "build_apollo_operation_catalog",
    "get_apollo_operation",
]
