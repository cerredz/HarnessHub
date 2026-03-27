"""Thin Salesforge API client wrapper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from harnessiq.providers.http import RequestExecutor, request_json
from harnessiq.providers.salesforge.operations import get_salesforge_operation
from harnessiq.providers.salesforge.api import (
    DEFAULT_BASE_URL,
    build_headers,
    contact_activity_url,
    contact_url,
    contacts_url,
    mailbox_url,
    mailboxes_url,
    sequence_contact_url,
    sequence_contacts_url,
    sequence_pause_url,
    sequence_resume_url,
    sequence_stats_url,
    sequence_url,
    sequences_url,
    unsubscribe_url,
)
from harnessiq.providers.salesforge.requests import (
    build_add_contacts_to_sequence_request,
    build_add_unsubscribe_request,
    build_create_contact_request,
    build_create_sequence_request,
    build_remove_unsubscribe_request,
    build_update_contact_request,
    build_update_sequence_request,
)
from harnessiq.shared.dtos import ProviderPayloadRequestDTO, ProviderPayloadResultDTO
from harnessiq.shared.provider_payloads import execute_payload_operation


@dataclass(frozen=True, slots=True)
class SalesforgeClient:
    """Minimal Salesforge API client.

    Args:
        api_key: Salesforge API key passed as ``Authorization: Bearer {api_key}``.
        base_url: Override the default API base URL.
        timeout_seconds: Per-request timeout in seconds.
        request_executor: Pluggable HTTP executor for testing.
    """

    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 60.0
    request_executor: RequestExecutor = request_json

    # --- Sequence methods ---

    def list_sequences(self) -> Any:
        """List all sequences."""
        return self._request("GET", sequences_url(self.base_url))

    def create_sequence(
        self,
        *,
        name: str,
        mailbox_id: str | int,
        daily_limit: int | None = None,
        timezone: str | None = None,
        track_open: bool | None = None,
        track_click: bool | None = None,
        stop_on_auto_reply: bool | None = None,
    ) -> Any:
        """Create a new sequence."""
        payload = build_create_sequence_request(
            name=name,
            mailbox_id=mailbox_id,
            daily_limit=daily_limit,
            timezone=timezone,
            track_open=track_open,
            track_click=track_click,
            stop_on_auto_reply=stop_on_auto_reply,
        )
        return self._request("POST", sequences_url(self.base_url), json_body=payload)

    def get_sequence(self, sequence_id: str | int) -> Any:
        """Get a sequence by ID."""
        return self._request("GET", sequence_url(sequence_id, self.base_url))

    def update_sequence(
        self,
        sequence_id: str | int,
        *,
        name: str | None = None,
        mailbox_id: str | int | None = None,
        daily_limit: int | None = None,
        timezone: str | None = None,
        track_open: bool | None = None,
        track_click: bool | None = None,
        stop_on_auto_reply: bool | None = None,
    ) -> Any:
        """Update a sequence."""
        payload = build_update_sequence_request(
            name=name,
            mailbox_id=mailbox_id,
            daily_limit=daily_limit,
            timezone=timezone,
            track_open=track_open,
            track_click=track_click,
            stop_on_auto_reply=stop_on_auto_reply,
        )
        return self._request("PATCH", sequence_url(sequence_id, self.base_url), json_body=payload)

    def delete_sequence(self, sequence_id: str | int) -> Any:
        """Delete a sequence."""
        return self._request("DELETE", sequence_url(sequence_id, self.base_url))

    def pause_sequence(self, sequence_id: str | int) -> Any:
        """Pause a sequence."""
        return self._request("POST", sequence_pause_url(sequence_id, self.base_url))

    def resume_sequence(self, sequence_id: str | int) -> Any:
        """Resume a paused sequence."""
        return self._request("POST", sequence_resume_url(sequence_id, self.base_url))

    def get_sequence_stats(self, sequence_id: str | int) -> Any:
        """Get stats for a sequence."""
        return self._request("GET", sequence_stats_url(sequence_id, self.base_url))

    def add_contacts_to_sequence(
        self,
        sequence_id: str | int,
        contacts: list[dict[str, Any]],
    ) -> Any:
        """Add contacts to a sequence."""
        payload = build_add_contacts_to_sequence_request(contacts)
        return self._request("POST", sequence_contacts_url(sequence_id, self.base_url), json_body=payload)

    def list_sequence_contacts(self, sequence_id: str | int) -> Any:
        """List contacts in a sequence."""
        return self._request("GET", sequence_contacts_url(sequence_id, self.base_url))

    def remove_contact_from_sequence(
        self,
        sequence_id: str | int,
        contact_id: str | int,
    ) -> Any:
        """Remove a contact from a sequence."""
        return self._request("DELETE", sequence_contact_url(sequence_id, contact_id, self.base_url))

    # --- Contact methods ---

    def list_contacts(self) -> Any:
        """List all contacts."""
        return self._request("GET", contacts_url(self.base_url))

    def create_contact(
        self,
        *,
        first_name: str,
        last_name: str,
        email: str,
        company_name: str | None = None,
        title: str | None = None,
        linkedin_url: str | None = None,
        phone: str | None = None,
        custom_fields: dict[str, Any] | None = None,
    ) -> Any:
        """Create a new contact."""
        payload = build_create_contact_request(
            first_name=first_name,
            last_name=last_name,
            email=email,
            company_name=company_name,
            title=title,
            linkedin_url=linkedin_url,
            phone=phone,
            custom_fields=custom_fields,
        )
        return self._request("POST", contacts_url(self.base_url), json_body=payload)

    def get_contact(self, contact_id: str | int) -> Any:
        """Get a contact by ID."""
        return self._request("GET", contact_url(contact_id, self.base_url))

    def update_contact(
        self,
        contact_id: str | int,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
        company_name: str | None = None,
        title: str | None = None,
        linkedin_url: str | None = None,
        phone: str | None = None,
        custom_fields: dict[str, Any] | None = None,
    ) -> Any:
        """Update a contact."""
        payload = build_update_contact_request(
            first_name=first_name,
            last_name=last_name,
            email=email,
            company_name=company_name,
            title=title,
            linkedin_url=linkedin_url,
            phone=phone,
            custom_fields=custom_fields,
        )
        return self._request("PATCH", contact_url(contact_id, self.base_url), json_body=payload)

    def delete_contact(self, contact_id: str | int) -> Any:
        """Delete a contact."""
        return self._request("DELETE", contact_url(contact_id, self.base_url))

    def get_contact_activity(self, contact_id: str | int) -> Any:
        """Get activity history for a contact."""
        return self._request("GET", contact_activity_url(contact_id, self.base_url))

    # --- Mailbox methods ---

    def list_mailboxes(self) -> Any:
        """List all mailboxes."""
        return self._request("GET", mailboxes_url(self.base_url))

    def get_mailbox(self, mailbox_id: str | int) -> Any:
        """Get a mailbox by ID."""
        return self._request("GET", mailbox_url(mailbox_id, self.base_url))

    # --- Unsubscribe methods ---

    def list_unsubscribed(self) -> Any:
        """List all unsubscribed emails."""
        return self._request("GET", unsubscribe_url(self.base_url))

    def add_unsubscribe(self, email: str) -> Any:
        """Add an email to the unsubscribe list."""
        payload = build_add_unsubscribe_request(email)
        return self._request("POST", unsubscribe_url(self.base_url), json_body=payload)

    def remove_unsubscribe(self, email: str) -> Any:
        """Remove an email from the unsubscribe list."""
        payload = build_remove_unsubscribe_request(email)
        return self._request("DELETE", unsubscribe_url(self.base_url), json_body=payload)

    def execute_operation(self, request: ProviderPayloadRequestDTO) -> ProviderPayloadResultDTO:
        """Execute one Salesforge operation from a DTO envelope."""

        get_salesforge_operation(request.operation)
        return execute_payload_operation(self, request)

    # --- Internal ---

    def _request(
        self,
        method: str,
        url: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        return self.request_executor(
            method,
            url,
            headers=build_headers(self.api_key),
            json_body=dict(json_body) if json_body is not None else None,
            timeout_seconds=self.timeout_seconds,
        )
