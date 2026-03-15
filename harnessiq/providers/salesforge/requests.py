"""Salesforge REST API request payload builders."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from harnessiq.providers.base import omit_none_values


# ---------------------------------------------------------------------------
# Sequence request builders
# ---------------------------------------------------------------------------


def build_create_sequence_request(
    *,
    name: str,
    mailbox_id: str | int,
    daily_limit: int | None = None,
    timezone: str | None = None,
    track_open: bool | None = None,
    track_click: bool | None = None,
    stop_on_auto_reply: bool | None = None,
) -> dict[str, object]:
    """Build a request body to create a new sequence."""
    return omit_none_values(
        {
            "name": name,
            "mailboxId": mailbox_id,
            "dailyLimit": daily_limit,
            "timezone": timezone,
            "trackOpen": track_open,
            "trackClick": track_click,
            "stopOnAutoReply": stop_on_auto_reply,
        }
    )


def build_update_sequence_request(
    *,
    name: str | None = None,
    mailbox_id: str | int | None = None,
    daily_limit: int | None = None,
    timezone: str | None = None,
    track_open: bool | None = None,
    track_click: bool | None = None,
    stop_on_auto_reply: bool | None = None,
) -> dict[str, object]:
    """Build a PATCH request body to update a sequence."""
    return omit_none_values(
        {
            "name": name,
            "mailboxId": mailbox_id,
            "dailyLimit": daily_limit,
            "timezone": timezone,
            "trackOpen": track_open,
            "trackClick": track_click,
            "stopOnAutoReply": stop_on_auto_reply,
        }
    )


def build_add_contacts_to_sequence_request(
    contacts: list[dict[str, Any]],
) -> dict[str, object]:
    """Build a request body to add contacts to a sequence."""
    return {"contacts": deepcopy(contacts)}


# ---------------------------------------------------------------------------
# Contact request builders
# ---------------------------------------------------------------------------


def build_create_contact_request(
    *,
    first_name: str,
    last_name: str,
    email: str,
    company_name: str | None = None,
    title: str | None = None,
    linkedin_url: str | None = None,
    phone: str | None = None,
    custom_fields: dict[str, Any] | None = None,
) -> dict[str, object]:
    """Build a request body to create a new contact."""
    return omit_none_values(
        {
            "firstName": first_name,
            "lastName": last_name,
            "email": email,
            "companyName": company_name,
            "title": title,
            "linkedinUrl": linkedin_url,
            "phone": phone,
            "customFields": deepcopy(custom_fields) if custom_fields is not None else None,
        }
    )


def build_update_contact_request(
    *,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    company_name: str | None = None,
    title: str | None = None,
    linkedin_url: str | None = None,
    phone: str | None = None,
    custom_fields: dict[str, Any] | None = None,
) -> dict[str, object]:
    """Build a PATCH request body to update a contact."""
    return omit_none_values(
        {
            "firstName": first_name,
            "lastName": last_name,
            "email": email,
            "companyName": company_name,
            "title": title,
            "linkedinUrl": linkedin_url,
            "phone": phone,
            "customFields": deepcopy(custom_fields) if custom_fields is not None else None,
        }
    )


# ---------------------------------------------------------------------------
# Unsubscribe request builders
# ---------------------------------------------------------------------------


def build_add_unsubscribe_request(email: str) -> dict[str, object]:
    """Build a request body to add an email to the unsubscribe list."""
    return {"email": email}


def build_remove_unsubscribe_request(email: str) -> dict[str, object]:
    """Build a request body to remove an email from the unsubscribe list."""
    return {"email": email}
