"""Salesforge shared operation metadata."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass

SALESFORGE_API_PREFIX = "/public/api/v1"


@dataclass(frozen=True, slots=True)
class SalesforgeOperation:
    """Metadata for a single Salesforge API operation."""

    name: str
    category: str
    description: str

    def summary(self) -> str:
        return self.name


_CATALOG: OrderedDict[str, SalesforgeOperation] = OrderedDict(
    [
        # ── Sequences ─────────────────────────────────────────────────────
        (
            "list_sequences",
            SalesforgeOperation(
                name="list_sequences",
                category="Sequence",
                description="List all email sequences in the workspace.",
            ),
        ),
        (
            "create_sequence",
            SalesforgeOperation(
                name="create_sequence",
                category="Sequence",
                description="Create a new email sequence with name, mailbox, and settings.",
            ),
        ),
        (
            "get_sequence",
            SalesforgeOperation(
                name="get_sequence",
                category="Sequence",
                description="Retrieve a sequence by its ID.",
            ),
        ),
        (
            "update_sequence",
            SalesforgeOperation(
                name="update_sequence",
                category="Sequence",
                description="Update sequence settings such as name, mailbox, or daily limits.",
            ),
        ),
        (
            "delete_sequence",
            SalesforgeOperation(
                name="delete_sequence",
                category="Sequence",
                description="Delete a sequence permanently.",
            ),
        ),
        (
            "pause_sequence",
            SalesforgeOperation(
                name="pause_sequence",
                category="Sequence",
                description="Pause a running sequence.",
            ),
        ),
        (
            "resume_sequence",
            SalesforgeOperation(
                name="resume_sequence",
                category="Sequence",
                description="Resume a paused sequence.",
            ),
        ),
        (
            "get_sequence_stats",
            SalesforgeOperation(
                name="get_sequence_stats",
                category="Sequence",
                description="Retrieve open, click, and reply statistics for a sequence.",
            ),
        ),
        # ── Sequence contacts ─────────────────────────────────────────────
        (
            "add_contacts_to_sequence",
            SalesforgeOperation(
                name="add_contacts_to_sequence",
                category="Sequence Contact",
                description="Add one or more contacts to a sequence.",
            ),
        ),
        (
            "list_sequence_contacts",
            SalesforgeOperation(
                name="list_sequence_contacts",
                category="Sequence Contact",
                description="List all contacts enrolled in a sequence.",
            ),
        ),
        (
            "remove_contact_from_sequence",
            SalesforgeOperation(
                name="remove_contact_from_sequence",
                category="Sequence Contact",
                description="Remove a contact from a sequence.",
            ),
        ),
        # ── Contacts ──────────────────────────────────────────────────────
        (
            "list_contacts",
            SalesforgeOperation(
                name="list_contacts",
                category="Contact",
                description="List all contacts in the workspace.",
            ),
        ),
        (
            "create_contact",
            SalesforgeOperation(
                name="create_contact",
                category="Contact",
                description="Create a new contact with name, email, and optional profile fields.",
            ),
        ),
        (
            "get_contact",
            SalesforgeOperation(
                name="get_contact",
                category="Contact",
                description="Retrieve a contact by its ID.",
            ),
        ),
        (
            "update_contact",
            SalesforgeOperation(
                name="update_contact",
                category="Contact",
                description="Update contact fields such as name, title, or company.",
            ),
        ),
        (
            "delete_contact",
            SalesforgeOperation(
                name="delete_contact",
                category="Contact",
                description="Delete a contact permanently.",
            ),
        ),
        (
            "get_contact_activity",
            SalesforgeOperation(
                name="get_contact_activity",
                category="Contact",
                description="Retrieve email activity history for a contact.",
            ),
        ),
        # ── Mailboxes ─────────────────────────────────────────────────────
        (
            "list_mailboxes",
            SalesforgeOperation(
                name="list_mailboxes",
                category="Mailbox",
                description="List all connected sending mailboxes.",
            ),
        ),
        (
            "get_mailbox",
            SalesforgeOperation(
                name="get_mailbox",
                category="Mailbox",
                description="Retrieve a mailbox configuration by its ID.",
            ),
        ),
        # ── Unsubscribe ───────────────────────────────────────────────────
        (
            "list_unsubscribed",
            SalesforgeOperation(
                name="list_unsubscribed",
                category="Unsubscribe",
                description="List all globally unsubscribed email addresses.",
            ),
        ),
        (
            "add_unsubscribe",
            SalesforgeOperation(
                name="add_unsubscribe",
                category="Unsubscribe",
                description="Add an email address to the global unsubscribe list.",
            ),
        ),
        (
            "remove_unsubscribe",
            SalesforgeOperation(
                name="remove_unsubscribe",
                category="Unsubscribe",
                description="Remove an email address from the global unsubscribe list.",
            ),
        ),
    ]
)


def build_salesforge_operation_catalog() -> tuple[SalesforgeOperation, ...]:
    """Return all registered Salesforge operations as an ordered tuple."""
    return tuple(_CATALOG.values())


def get_salesforge_operation(name: str) -> SalesforgeOperation:
    """Return the operation for *name*, raising :exc:`ValueError` if unknown."""
    try:
        return _CATALOG[name]
    except KeyError:
        known = ", ".join(_CATALOG)
        raise ValueError(f"Unknown Salesforge operation '{name}'. Known: {known}") from None


__all__ = [
    "SALESFORGE_API_PREFIX",
    "SalesforgeOperation",
    "build_salesforge_operation_catalog",
    "get_salesforge_operation",
]
