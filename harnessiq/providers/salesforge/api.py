"""Salesforge endpoint and authentication helpers."""

from __future__ import annotations

from typing import Mapping

from harnessiq.providers.base import omit_none_values
from harnessiq.providers.http import join_url

from harnessiq.shared.providers import SALESFORGE_DEFAULT_BASE_URL as DEFAULT_BASE_URL
from harnessiq.shared.salesforge import SALESFORGE_API_PREFIX


def build_headers(
    api_key: str,
    *,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build the headers required for Salesforge API requests."""
    headers = omit_none_values({"Authorization": f"Bearer {api_key}"})
    if extra_headers:
        headers.update(extra_headers)
    return headers


# --- Sequence endpoints ---


def sequences_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the sequences list/create URL."""
    return join_url(base_url, f"{SALESFORGE_API_PREFIX}/sequence")


def sequence_url(sequence_id: str | int, base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the URL for a single sequence resource."""
    return join_url(base_url, f"{SALESFORGE_API_PREFIX}/sequence/{sequence_id}")


def sequence_pause_url(sequence_id: str | int, base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the URL to pause a sequence."""
    return join_url(base_url, f"{SALESFORGE_API_PREFIX}/sequence/{sequence_id}/pause")


def sequence_resume_url(sequence_id: str | int, base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the URL to resume a sequence."""
    return join_url(base_url, f"{SALESFORGE_API_PREFIX}/sequence/{sequence_id}/resume")


def sequence_stats_url(sequence_id: str | int, base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the URL to fetch sequence stats."""
    return join_url(base_url, f"{SALESFORGE_API_PREFIX}/sequence/{sequence_id}/stats")


def sequence_contacts_url(sequence_id: str | int, base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the URL to add/list contacts in a sequence."""
    return join_url(base_url, f"{SALESFORGE_API_PREFIX}/sequence/{sequence_id}/contact")


def sequence_contact_url(
    sequence_id: str | int,
    contact_id: str | int,
    base_url: str = DEFAULT_BASE_URL,
) -> str:
    """Return the URL to remove a contact from a sequence."""
    return join_url(base_url, f"{SALESFORGE_API_PREFIX}/sequence/{sequence_id}/contact/{contact_id}")


# --- Contact endpoints ---


def contacts_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the contacts list/create URL."""
    return join_url(base_url, f"{SALESFORGE_API_PREFIX}/contact")


def contact_url(contact_id: str | int, base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the URL for a single contact resource."""
    return join_url(base_url, f"{SALESFORGE_API_PREFIX}/contact/{contact_id}")


def contact_activity_url(contact_id: str | int, base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the URL for contact activity history."""
    return join_url(base_url, f"{SALESFORGE_API_PREFIX}/contact/{contact_id}/activity")


# --- Mailbox endpoints ---


def mailboxes_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the mailboxes list URL."""
    return join_url(base_url, f"{SALESFORGE_API_PREFIX}/mailbox")


def mailbox_url(mailbox_id: str | int, base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the URL for a single mailbox resource."""
    return join_url(base_url, f"{SALESFORGE_API_PREFIX}/mailbox/{mailbox_id}")


# --- Unsubscribe endpoints ---


def unsubscribe_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the unsubscribe list URL."""
    return join_url(base_url, f"{SALESFORGE_API_PREFIX}/unsubscribe")

