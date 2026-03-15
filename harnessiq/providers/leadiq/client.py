"""Thin LeadIQ API client wrapper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from harnessiq.providers.http import RequestExecutor, request_json
from harnessiq.providers.leadiq.api import DEFAULT_BASE_URL, build_headers, graphql_url
from harnessiq.providers.leadiq.requests import (
    build_add_tag_to_contact_request,
    build_capture_leads_request,
    build_enrich_contact_request,
    build_find_person_by_linkedin_request,
    build_get_capture_status_request,
    build_get_captures_request,
    build_get_contact_details_request,
    build_get_tags_request,
    build_get_team_activity_request,
    build_remove_tag_from_contact_request,
    build_search_companies_request,
    build_search_contacts_request,
)


@dataclass(frozen=True, slots=True)
class LeadIQClient:
    """Minimal LeadIQ API client.

    All operations use the single ``POST /graphql`` endpoint.

    Args:
        api_key: LeadIQ API key passed in ``X-Api-Key`` header.
        base_url: Override the default API base URL.
        timeout_seconds: Per-request timeout in seconds.
        request_executor: Pluggable HTTP executor for testing.
    """

    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 60.0
    request_executor: RequestExecutor = request_json

    def search_contacts(
        self,
        *,
        name: str | None = None,
        email: str | None = None,
        company: str | None = None,
        title: str | None = None,
        location: str | None = None,
        linkedin_url: str | None = None,
        page: int | None = None,
        per_page: int | None = None,
    ) -> Any:
        """Search contacts by filter criteria."""
        payload = build_search_contacts_request(
            name=name,
            email=email,
            company=company,
            title=title,
            location=location,
            linkedin_url=linkedin_url,
            page=page,
            per_page=per_page,
        )
        return self._graphql(payload)

    def search_companies(
        self,
        *,
        name: str | None = None,
        domain: str | None = None,
        industry: str | None = None,
        employee_count_min: int | None = None,
        employee_count_max: int | None = None,
        page: int | None = None,
        per_page: int | None = None,
    ) -> Any:
        """Search companies by filter criteria."""
        payload = build_search_companies_request(
            name=name,
            domain=domain,
            industry=industry,
            employee_count_min=employee_count_min,
            employee_count_max=employee_count_max,
            page=page,
            per_page=per_page,
        )
        return self._graphql(payload)

    def find_person_by_linkedin(self, linkedin_url: str) -> Any:
        """Look up a person by their LinkedIn profile URL."""
        return self._graphql(build_find_person_by_linkedin_request(linkedin_url))

    def enrich_contact(self, contact_id: str) -> Any:
        """Enrich a contact to reveal email and phone information."""
        return self._graphql(build_enrich_contact_request(contact_id))

    def capture_leads(self, contacts: list[dict[str, Any]]) -> Any:
        """Capture a batch of leads into the workspace."""
        return self._graphql(build_capture_leads_request(contacts))

    def get_captures(
        self,
        *,
        page: int | None = None,
        per_page: int | None = None,
    ) -> Any:
        """List previously captured leads."""
        return self._graphql(build_get_captures_request(page=page, per_page=per_page))

    def get_contact_details(self, contact_id: str) -> Any:
        """Retrieve full details for a contact by ID."""
        return self._graphql(build_get_contact_details_request(contact_id))

    def get_capture_status(self, capture_id: str) -> Any:
        """Get the status of a capture operation."""
        return self._graphql(build_get_capture_status_request(capture_id))

    def get_team_activity(
        self,
        *,
        page: int | None = None,
        per_page: int | None = None,
    ) -> Any:
        """Retrieve recent team activity."""
        return self._graphql(build_get_team_activity_request(page=page, per_page=per_page))

    def get_tags(self) -> Any:
        """List all tags in the workspace."""
        return self._graphql(build_get_tags_request())

    def add_tag_to_contact(self, contact_id: str, tag_id: str) -> Any:
        """Apply a tag to a contact."""
        return self._graphql(build_add_tag_to_contact_request(contact_id, tag_id))

    def remove_tag_from_contact(self, contact_id: str, tag_id: str) -> Any:
        """Remove a tag from a contact."""
        return self._graphql(build_remove_tag_from_contact_request(contact_id, tag_id))

    def _graphql(self, payload: dict[str, object]) -> Any:
        return self.request_executor(
            "POST",
            graphql_url(self.base_url),
            headers=build_headers(self.api_key),
            json_body=dict(payload),
            timeout_seconds=self.timeout_seconds,
        )
