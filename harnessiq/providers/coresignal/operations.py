"""Coresignal operation catalog."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CoreSignalOperation:
    """Metadata for a single Coresignal API operation."""

    name: str
    category: str
    description: str

    def summary(self) -> str:
        return self.name


_CATALOG: OrderedDict[str, CoreSignalOperation] = OrderedDict(
    [
        # ── Employee ──────────────────────────────────────────────────────
        (
            "search_employees_by_filter",
            CoreSignalOperation(
                name="search_employees_by_filter",
                category="Employee",
                description="Search employee records by name, title, company, or location.",
            ),
        ),
        (
            "get_employee",
            CoreSignalOperation(
                name="get_employee",
                category="Employee",
                description="Retrieve a full employee record by its Coresignal ID.",
            ),
        ),
        (
            "search_employees_es_dsl",
            CoreSignalOperation(
                name="search_employees_es_dsl",
                category="Employee",
                description="Search employees using an Elasticsearch DSL query for complex filters.",
            ),
        ),
        # ── Company ───────────────────────────────────────────────────────
        (
            "search_companies_by_filter",
            CoreSignalOperation(
                name="search_companies_by_filter",
                category="Company",
                description="Search company records by name, website, industry, or country.",
            ),
        ),
        (
            "get_company",
            CoreSignalOperation(
                name="get_company",
                category="Company",
                description="Retrieve a full company record by its Coresignal ID.",
            ),
        ),
        (
            "search_companies_es_dsl",
            CoreSignalOperation(
                name="search_companies_es_dsl",
                category="Company",
                description="Search companies using an Elasticsearch DSL query for complex filters.",
            ),
        ),
        # ── Jobs ──────────────────────────────────────────────────────────
        (
            "search_jobs_by_filter",
            CoreSignalOperation(
                name="search_jobs_by_filter",
                category="Job",
                description="Search job postings by title, company, location, or date range.",
            ),
        ),
        (
            "get_job",
            CoreSignalOperation(
                name="get_job",
                category="Job",
                description="Retrieve a full job posting record by its Coresignal ID.",
            ),
        ),
        (
            "search_jobs_es_dsl",
            CoreSignalOperation(
                name="search_jobs_es_dsl",
                category="Job",
                description="Search job postings using an Elasticsearch DSL query.",
            ),
        ),
    ]
)


def build_coresignal_operation_catalog() -> tuple[CoreSignalOperation, ...]:
    """Return all registered Coresignal operations as an ordered tuple."""
    return tuple(_CATALOG.values())


def get_coresignal_operation(name: str) -> CoreSignalOperation:
    """Return the operation for *name*, raising :exc:`ValueError` if unknown."""
    try:
        return _CATALOG[name]
    except KeyError:
        known = ", ".join(_CATALOG)
        raise ValueError(f"Unknown Coresignal operation '{name}'. Known: {known}") from None


__all__ = [
    "CoreSignalOperation",
    "build_coresignal_operation_catalog",
    "get_coresignal_operation",
]
