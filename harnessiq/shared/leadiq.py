"""LeadIQ shared operation metadata."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LeadIQOperation:
    """Metadata for a single LeadIQ API operation."""

    name: str
    category: str
    description: str

    def summary(self) -> str:
        return self.name


_CATALOG: OrderedDict[str, LeadIQOperation] = OrderedDict(
    [
        # ── Contacts ──────────────────────────────────────────────────────
        (
            "search_contacts",
            LeadIQOperation(
                name="search_contacts",
                category="Contact",
                description="Search contacts by name, email, title, company, or location.",
            ),
        ),
        (
            "find_person_by_linkedin",
            LeadIQOperation(
                name="find_person_by_linkedin",
                category="Contact",
                description="Look up a person's profile by their LinkedIn URL.",
            ),
        ),
        (
            "enrich_contact",
            LeadIQOperation(
                name="enrich_contact",
                category="Contact",
                description="Enrich a contact to reveal verified email and phone data.",
            ),
        ),
        (
            "get_contact_details",
            LeadIQOperation(
                name="get_contact_details",
                category="Contact",
                description="Retrieve full details for a contact by its ID.",
            ),
        ),
        # ── Companies ─────────────────────────────────────────────────────
        (
            "search_companies",
            LeadIQOperation(
                name="search_companies",
                category="Company",
                description="Search companies by name, domain, industry, or employee count.",
            ),
        ),
        # ── Leads / captures ──────────────────────────────────────────────
        (
            "capture_leads",
            LeadIQOperation(
                name="capture_leads",
                category="Lead",
                description="Capture a batch of contact records into the workspace.",
            ),
        ),
        (
            "get_captures",
            LeadIQOperation(
                name="get_captures",
                category="Lead",
                description="List previously captured lead records.",
            ),
        ),
        (
            "get_capture_status",
            LeadIQOperation(
                name="get_capture_status",
                category="Lead",
                description="Get the status of a capture operation by its ID.",
            ),
        ),
        # ── Team ──────────────────────────────────────────────────────────
        (
            "get_team_activity",
            LeadIQOperation(
                name="get_team_activity",
                category="Team",
                description="Retrieve recent activity across the team workspace.",
            ),
        ),
        # ── Tags ──────────────────────────────────────────────────────────
        (
            "get_tags",
            LeadIQOperation(
                name="get_tags",
                category="Tag",
                description="List all tags available in the workspace.",
            ),
        ),
        (
            "add_tag_to_contact",
            LeadIQOperation(
                name="add_tag_to_contact",
                category="Tag",
                description="Apply a tag to a contact.",
            ),
        ),
        (
            "remove_tag_from_contact",
            LeadIQOperation(
                name="remove_tag_from_contact",
                category="Tag",
                description="Remove a tag from a contact.",
            ),
        ),
    ]
)


def build_leadiq_operation_catalog() -> tuple[LeadIQOperation, ...]:
    """Return all registered LeadIQ operations as an ordered tuple."""
    return tuple(_CATALOG.values())


def get_leadiq_operation(name: str) -> LeadIQOperation:
    """Return the operation for *name*, raising :exc:`ValueError` if unknown."""
    try:
        return _CATALOG[name]
    except KeyError:
        known = ", ".join(_CATALOG)
        raise ValueError(f"Unknown LeadIQ operation '{name}'. Known: {known}") from None


__all__ = [
    "LeadIQOperation",
    "build_leadiq_operation_catalog",
    "get_leadiq_operation",
]
