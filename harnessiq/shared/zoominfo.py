"""ZoomInfo operation catalog."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ZoomInfoOperation:
    """Metadata for a single ZoomInfo API operation."""

    name: str
    category: str
    description: str

    def summary(self) -> str:
        return self.name


_CATALOG: OrderedDict[str, ZoomInfoOperation] = OrderedDict(
    [
        # ── Contact search ────────────────────────────────────────────────
        (
            "search_contacts",
            ZoomInfoOperation(
                name="search_contacts",
                category="Contact",
                description="Search contacts using output fields and match filter criteria.",
            ),
        ),
        # ── Company search ────────────────────────────────────────────────
        (
            "search_companies",
            ZoomInfoOperation(
                name="search_companies",
                category="Company",
                description="Search companies using output fields and match filter criteria.",
            ),
        ),
        # ── Intent data ───────────────────────────────────────────────────
        (
            "search_intent",
            ZoomInfoOperation(
                name="search_intent",
                category="Intent",
                description="Search buying-intent signals for companies by topic.",
            ),
        ),
        # ── News & scoops ─────────────────────────────────────────────────
        (
            "search_news",
            ZoomInfoOperation(
                name="search_news",
                category="News",
                description="Search news signals relevant to target accounts.",
            ),
        ),
        (
            "search_scoops",
            ZoomInfoOperation(
                name="search_scoops",
                category="Scoop",
                description="Search business intelligence scoops (leadership changes, initiatives).",
            ),
        ),
        # ── Enrichment ────────────────────────────────────────────────────
        (
            "enrich_contact",
            ZoomInfoOperation(
                name="enrich_contact",
                category="Enrichment",
                description="Enrich contact data for one or more persons.",
            ),
        ),
        (
            "enrich_company",
            ZoomInfoOperation(
                name="enrich_company",
                category="Enrichment",
                description="Enrich company data for one or more organisations.",
            ),
        ),
        (
            "enrich_ip",
            ZoomInfoOperation(
                name="enrich_ip",
                category="Enrichment",
                description="Enrich company and contact data for a given IP address.",
            ),
        ),
        # ── Bulk enrichment ───────────────────────────────────────────────
        (
            "bulk_enrich_contacts",
            ZoomInfoOperation(
                name="bulk_enrich_contacts",
                category="Bulk",
                description="Submit a bulk contact enrichment job for multiple persons.",
            ),
        ),
        (
            "bulk_enrich_companies",
            ZoomInfoOperation(
                name="bulk_enrich_companies",
                category="Bulk",
                description="Submit a bulk company enrichment job for multiple organisations.",
            ),
        ),
        # ── Utility ───────────────────────────────────────────────────────
        (
            "lookup_output_fields",
            ZoomInfoOperation(
                name="lookup_output_fields",
                category="Utility",
                description="Retrieve the list of available output fields for a given entity type.",
            ),
        ),
        (
            "get_usage",
            ZoomInfoOperation(
                name="get_usage",
                category="Utility",
                description="Retrieve API usage and quota information for the account.",
            ),
        ),
    ]
)


def build_zoominfo_operation_catalog() -> tuple[ZoomInfoOperation, ...]:
    """Return all registered ZoomInfo operations as an ordered tuple."""
    return tuple(_CATALOG.values())


def get_zoominfo_operation(name: str) -> ZoomInfoOperation:
    """Return the operation for *name*, raising :exc:`ValueError` if unknown."""
    try:
        return _CATALOG[name]
    except KeyError:
        known = ", ".join(_CATALOG)
        raise ValueError(f"Unknown ZoomInfo operation '{name}'. Known: {known}") from None


__all__ = [
    "ZoomInfoOperation",
    "build_zoominfo_operation_catalog",
    "get_zoominfo_operation",
]
