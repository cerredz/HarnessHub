"""Proxycurl operation catalog.

NOTE: Proxycurl shut down in January 2025 following a LinkedIn lawsuit.
This module is preserved for reference only and will not produce live responses.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProxycurlOperation:
    """Metadata for a single Proxycurl API operation."""

    name: str
    category: str
    description: str

    def summary(self) -> str:
        return self.name


_CATALOG: OrderedDict[str, ProxycurlOperation] = OrderedDict(
    [
        # ── Person ────────────────────────────────────────────────────────
        (
            "scrape_person_profile",
            ProxycurlOperation(
                name="scrape_person_profile",
                category="Person",
                description="Scrape a LinkedIn person profile by URL.",
            ),
        ),
        (
            "resolve_person_profile",
            ProxycurlOperation(
                name="resolve_person_profile",
                category="Person",
                description="Find the LinkedIn profile URL for a person by name and company domain.",
            ),
        ),
        (
            "lookup_person_by_email",
            ProxycurlOperation(
                name="lookup_person_by_email",
                category="Person",
                description="Look up a LinkedIn profile by email address.",
            ),
        ),
        # ── Company ───────────────────────────────────────────────────────
        (
            "scrape_company_profile",
            ProxycurlOperation(
                name="scrape_company_profile",
                category="Company",
                description="Scrape a LinkedIn company profile by URL.",
            ),
        ),
        (
            "resolve_company_profile",
            ProxycurlOperation(
                name="resolve_company_profile",
                category="Company",
                description="Find the LinkedIn URL for a company by name or domain.",
            ),
        ),
        (
            "list_company_employees",
            ProxycurlOperation(
                name="list_company_employees",
                category="Company",
                description="List employees of a LinkedIn company, with optional role and country filters.",
            ),
        ),
        # ── Jobs ──────────────────────────────────────────────────────────
        (
            "list_company_jobs",
            ProxycurlOperation(
                name="list_company_jobs",
                category="Job",
                description="List open job postings from a LinkedIn company page.",
            ),
        ),
        (
            "search_jobs",
            ProxycurlOperation(
                name="search_jobs",
                category="Job",
                description="Search LinkedIn job postings by keyword, location, and type.",
            ),
        ),
        # ── Email & contact ───────────────────────────────────────────────
        (
            "resolve_email_to_profile",
            ProxycurlOperation(
                name="resolve_email_to_profile",
                category="Email",
                description="Resolve an email address to a LinkedIn profile.",
            ),
        ),
        (
            "get_personal_emails",
            ProxycurlOperation(
                name="get_personal_emails",
                category="Email",
                description="Retrieve personal email addresses for a LinkedIn profile.",
            ),
        ),
        (
            "get_personal_contacts",
            ProxycurlOperation(
                name="get_personal_contacts",
                category="Email",
                description="Retrieve personal phone numbers for a LinkedIn profile.",
            ),
        ),
    ]
)


def build_proxycurl_operation_catalog() -> tuple[ProxycurlOperation, ...]:
    """Return all registered Proxycurl operations as an ordered tuple."""
    return tuple(_CATALOG.values())


def get_proxycurl_operation(name: str) -> ProxycurlOperation:
    """Return the operation for *name*, raising :exc:`ValueError` if unknown."""
    try:
        return _CATALOG[name]
    except KeyError:
        known = ", ".join(_CATALOG)
        raise ValueError(f"Unknown Proxycurl operation '{name}'. Known: {known}") from None


__all__ = [
    "ProxycurlOperation",
    "build_proxycurl_operation_catalog",
    "get_proxycurl_operation",
]
