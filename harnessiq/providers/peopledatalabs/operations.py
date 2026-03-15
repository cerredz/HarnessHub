"""People Data Labs operation catalog."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PeopleDataLabsOperation:
    """Metadata for a single People Data Labs API operation."""

    name: str
    category: str
    description: str

    def summary(self) -> str:
        return self.name


_CATALOG: OrderedDict[str, PeopleDataLabsOperation] = OrderedDict(
    [
        # ── Person ────────────────────────────────────────────────────────
        (
            "enrich_person",
            PeopleDataLabsOperation(
                name="enrich_person",
                category="Person",
                description="Enrich a person record by email, phone, name, or LinkedIn URL.",
            ),
        ),
        (
            "identify_person",
            PeopleDataLabsOperation(
                name="identify_person",
                category="Person",
                description="Identify a person and retrieve all matching profiles.",
            ),
        ),
        (
            "search_people",
            PeopleDataLabsOperation(
                name="search_people",
                category="Person",
                description="Search people using Elasticsearch DSL query or SQL.",
            ),
        ),
        (
            "bulk_enrich_people",
            PeopleDataLabsOperation(
                name="bulk_enrich_people",
                category="Person",
                description="Bulk enrich multiple person records in a single request.",
            ),
        ),
        # ── Company ───────────────────────────────────────────────────────
        (
            "enrich_company",
            PeopleDataLabsOperation(
                name="enrich_company",
                category="Company",
                description="Enrich a company record by name, website, or LinkedIn URL.",
            ),
        ),
        (
            "search_companies",
            PeopleDataLabsOperation(
                name="search_companies",
                category="Company",
                description="Search companies using Elasticsearch DSL query or SQL.",
            ),
        ),
        (
            "bulk_enrich_companies",
            PeopleDataLabsOperation(
                name="bulk_enrich_companies",
                category="Company",
                description="Bulk enrich multiple company records in a single request.",
            ),
        ),
        # ── School ────────────────────────────────────────────────────────
        (
            "enrich_school",
            PeopleDataLabsOperation(
                name="enrich_school",
                category="School",
                description="Enrich a school or university record by name or website.",
            ),
        ),
        # ── Location ──────────────────────────────────────────────────────
        (
            "clean_location",
            PeopleDataLabsOperation(
                name="clean_location",
                category="Location",
                description="Clean and normalize a raw location string.",
            ),
        ),
        # ── Utility ───────────────────────────────────────────────────────
        (
            "autocomplete",
            PeopleDataLabsOperation(
                name="autocomplete",
                category="Utility",
                description="Autocomplete values for a given PDL field (e.g., job_title, industry).",
            ),
        ),
        (
            "enrich_job_title",
            PeopleDataLabsOperation(
                name="enrich_job_title",
                category="Utility",
                description="Normalize and enrich a job title string.",
            ),
        ),
    ]
)


def build_peopledatalabs_operation_catalog() -> tuple[PeopleDataLabsOperation, ...]:
    """Return all registered People Data Labs operations as an ordered tuple."""
    return tuple(_CATALOG.values())


def get_peopledatalabs_operation(name: str) -> PeopleDataLabsOperation:
    """Return the operation for *name*, raising :exc:`ValueError` if unknown."""
    try:
        return _CATALOG[name]
    except KeyError:
        known = ", ".join(_CATALOG)
        raise ValueError(f"Unknown PDL operation '{name}'. Known: {known}") from None


__all__ = [
    "PeopleDataLabsOperation",
    "build_peopledatalabs_operation_catalog",
    "get_peopledatalabs_operation",
]
