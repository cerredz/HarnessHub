"""Snov.io operation catalog."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SnovioOperation:
    """Metadata for a single Snov.io API operation."""

    name: str
    category: str
    description: str

    def summary(self) -> str:
        return self.name


_CATALOG: OrderedDict[str, SnovioOperation] = OrderedDict(
    [
        # ── Email discovery ───────────────────────────────────────────────
        (
            "domain_search",
            SnovioOperation(
                name="domain_search",
                category="Email Discovery",
                description="Search for email addresses associated with a domain.",
            ),
        ),
        (
            "get_emails_count",
            SnovioOperation(
                name="get_emails_count",
                category="Email Discovery",
                description="Count the number of emails available for a domain.",
            ),
        ),
        (
            "get_emails_from_names",
            SnovioOperation(
                name="get_emails_from_names",
                category="Email Discovery",
                description="Find email addresses for a person by first name, last name, and domain.",
            ),
        ),
        (
            "get_email_info",
            SnovioOperation(
                name="get_email_info",
                category="Email Discovery",
                description="Retrieve full profile information for a known email address.",
            ),
        ),
        (
            "verify_email",
            SnovioOperation(
                name="verify_email",
                category="Email Discovery",
                description="Verify the deliverability of an email address.",
            ),
        ),
        (
            "get_profile_emails",
            SnovioOperation(
                name="get_profile_emails",
                category="Email Discovery",
                description="Retrieve emails associated with a social profile URL.",
            ),
        ),
        (
            "url_search",
            SnovioOperation(
                name="url_search",
                category="Email Discovery",
                description="Find a prospect record from a LinkedIn or social profile URL.",
            ),
        ),
        # ── Prospects ─────────────────────────────────────────────────────
        (
            "get_prospect",
            SnovioOperation(
                name="get_prospect",
                category="Prospect",
                description="Retrieve a prospect record by its ID.",
            ),
        ),
        (
            "add_prospect",
            SnovioOperation(
                name="add_prospect",
                category="Prospect",
                description="Add a new prospect to a list with full contact details.",
            ),
        ),
        (
            "update_prospect",
            SnovioOperation(
                name="update_prospect",
                category="Prospect",
                description="Update fields on an existing prospect record.",
            ),
        ),
        (
            "delete_prospect",
            SnovioOperation(
                name="delete_prospect",
                category="Prospect",
                description="Delete a prospect by ID.",
            ),
        ),
        # ── Prospect lists ────────────────────────────────────────────────
        (
            "get_prospect_lists",
            SnovioOperation(
                name="get_prospect_lists",
                category="Prospect List",
                description="Return all prospect lists for the account.",
            ),
        ),
        (
            "get_list",
            SnovioOperation(
                name="get_list",
                category="Prospect List",
                description="Return a specific prospect list by ID.",
            ),
        ),
        (
            "add_to_list",
            SnovioOperation(
                name="add_to_list",
                category="Prospect List",
                description="Add an email address to a prospect list.",
            ),
        ),
        (
            "delete_from_list",
            SnovioOperation(
                name="delete_from_list",
                category="Prospect List",
                description="Remove an email address from a prospect list.",
            ),
        ),
        # ── Campaigns ─────────────────────────────────────────────────────
        (
            "get_all_campaigns",
            SnovioOperation(
                name="get_all_campaigns",
                category="Campaign",
                description="List all email campaigns for the account.",
            ),
        ),
        (
            "get_campaign",
            SnovioOperation(
                name="get_campaign",
                category="Campaign",
                description="Retrieve campaign details and statistics by ID.",
            ),
        ),
        (
            "get_campaign_recipients",
            SnovioOperation(
                name="get_campaign_recipients",
                category="Campaign",
                description="List recipients for a campaign, optionally filtered by status.",
            ),
        ),
        (
            "get_campaign_recipient_status",
            SnovioOperation(
                name="get_campaign_recipient_status",
                category="Campaign",
                description="Get the status of a specific email address in a campaign.",
            ),
        ),
        (
            "add_to_campaign",
            SnovioOperation(
                name="add_to_campaign",
                category="Campaign",
                description="Add a list of email addresses to a campaign.",
            ),
        ),
        (
            "start_campaign",
            SnovioOperation(
                name="start_campaign",
                category="Campaign",
                description="Start or resume a paused campaign.",
            ),
        ),
        (
            "pause_campaign",
            SnovioOperation(
                name="pause_campaign",
                category="Campaign",
                description="Pause a running campaign.",
            ),
        ),
        # ── Account ───────────────────────────────────────────────────────
        (
            "get_user_info",
            SnovioOperation(
                name="get_user_info",
                category="Account",
                description="Retrieve current user account information and credit balance.",
            ),
        ),
    ]
)


def build_snovio_operation_catalog() -> tuple[SnovioOperation, ...]:
    """Return all registered Snov.io operations as an ordered tuple."""
    return tuple(_CATALOG.values())


def get_snovio_operation(name: str) -> SnovioOperation:
    """Return the operation for *name*, raising :exc:`ValueError` if unknown."""
    try:
        return _CATALOG[name]
    except KeyError:
        known = ", ".join(_CATALOG)
        raise ValueError(f"Unknown Snov.io operation '{name}'. Known: {known}") from None


__all__ = [
    "SnovioOperation",
    "build_snovio_operation_catalog",
    "get_snovio_operation",
]
