"""Hunter.io shared operation metadata."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Literal, Sequence

PayloadKind = Literal["none", "object"]


@dataclass(frozen=True, slots=True)
class HunterOperation:
    """Declarative metadata for one Hunter.io API operation."""

    name: str
    category: str
    method: Literal["GET", "POST", "PUT", "DELETE"]
    path_hint: str
    required_path_params: tuple[str, ...] = ()
    payload_kind: PayloadKind = "none"
    payload_required: bool = False
    allow_query: bool = False
    required_query_params: tuple[str, ...] = ()
    required_any_of_sets: tuple[tuple[tuple[str, ...], ...], ...] = ()

    def summary(self) -> str:
        return f"{self.name} ({self.method} {self.path_hint})"


@dataclass(frozen=True, slots=True)
class HunterPreparedRequest:
    """A validated Hunter request ready for execution."""

    operation: HunterOperation
    method: str
    path: str
    url: str
    headers: dict[str, str]
    json_body: Any | None


def _op(
    name: str,
    category: str,
    method: Literal["GET", "POST", "PUT", "DELETE"],
    path_hint: str,
    *,
    required_path_params: Sequence[str] = (),
    payload_kind: PayloadKind = "none",
    payload_required: bool = False,
    allow_query: bool = False,
    required_query_params: Sequence[str] = (),
    required_any_of_sets: Sequence[Sequence[Sequence[str]]] = (),
) -> tuple[str, HunterOperation]:
    normalized_any_of_sets = tuple(
        tuple(tuple(field_name for field_name in combination) for combination in option_set)
        for option_set in required_any_of_sets
    )
    return (
        name,
        HunterOperation(
            name=name,
            category=category,
            method=method,
            path_hint=path_hint,
            required_path_params=tuple(required_path_params),
            payload_kind=payload_kind,
            payload_required=payload_required,
            allow_query=allow_query,
            required_query_params=tuple(required_query_params),
            required_any_of_sets=normalized_any_of_sets,
        ),
    )


_HUNTER_CATALOG: OrderedDict[str, HunterOperation] = OrderedDict(
    (
        _op(
            "domain_search",
            "Email Discovery",
            "GET",
            "/domain-search",
            allow_query=True,
            required_any_of_sets=(
                (("domain",), ("company",)),
            ),
        ),
        _op(
            "email_finder",
            "Email Discovery",
            "GET",
            "/email-finder",
            allow_query=True,
            required_any_of_sets=(
                (("domain",), ("company",)),
                (("full_name",), ("first_name", "last_name")),
            ),
        ),
        _op(
            "email_verifier",
            "Email Verification",
            "GET",
            "/email-verifier",
            allow_query=True,
            required_query_params=("email",),
        ),
        _op(
            "email_count",
            "Email Discovery",
            "GET",
            "/email-count",
            allow_query=True,
            required_any_of_sets=(
                (("domain",), ("company",)),
            ),
        ),
        _op("discover", "Company Discovery", "GET", "/discover", allow_query=True),
        _op(
            "email_enrichment",
            "Contact Enrichment",
            "GET",
            "/combined-enrichment",
            allow_query=True,
            required_query_params=("email",),
        ),
        _op(
            "company_enrichment",
            "Company Enrichment",
            "GET",
            "/company-enrichment",
            allow_query=True,
            required_any_of_sets=(
                (("domain",), ("company",)),
            ),
        ),
        _op("account_info", "Account Management", "GET", "/account"),
        _op("leads_list", "Lead Management", "GET", "/leads", allow_query=True),
        _op(
            "lead_get",
            "Lead Management",
            "GET",
            "/leads/{id}",
            required_path_params=("id",),
        ),
        _op(
            "lead_create",
            "Lead Management",
            "POST",
            "/leads",
            payload_kind="object",
            payload_required=True,
        ),
        _op(
            "lead_update",
            "Lead Management",
            "PUT",
            "/leads/{id}",
            required_path_params=("id",),
            payload_kind="object",
            payload_required=True,
        ),
        _op(
            "lead_delete",
            "Lead Management",
            "DELETE",
            "/leads/{id}",
            required_path_params=("id",),
        ),
        _op("campaigns_list", "Campaign Management", "GET", "/campaigns", allow_query=True),
    )
)


def build_hunter_operation_catalog() -> tuple[HunterOperation, ...]:
    """Return the supported Hunter operation catalog in stable order."""

    return tuple(_HUNTER_CATALOG.values())


def get_hunter_operation(operation_name: str) -> HunterOperation:
    """Return a supported Hunter operation or raise a clear error."""

    operation = _HUNTER_CATALOG.get(operation_name)
    if operation is None:
        available = ", ".join(_HUNTER_CATALOG)
        raise ValueError(
            f"Unsupported Hunter operation '{operation_name}'. Available: {available}."
        )
    return operation


__all__ = [
    "HunterOperation",
    "HunterPreparedRequest",
    "build_hunter_operation_catalog",
    "get_hunter_operation",
]
