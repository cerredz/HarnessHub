"""Thin Snov.io API client wrapper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib import parse

from harnessiq.providers.http import RequestExecutor, request_json
from harnessiq.providers.snovio.api import (
    DEFAULT_BASE_URL,
    access_token_url,
    add_prospect_url,
    add_to_campaign_url,
    add_to_list_url,
    all_campaigns_url,
    campaign_data_url,
    campaign_recipient_status_url,
    campaign_recipients_url,
    delete_from_list_url,
    delete_prospect_url,
    domain_search_url,
    email_info_url,
    email_verifier_url,
    emails_count_url,
    emails_from_names_url,
    get_list_url,
    pause_campaign_url,
    profile_emails_url,
    prospect_lists_url,
    prospect_url,
    start_campaign_url,
    update_prospect_url,
    url_search_url,
    user_info_url,
)
from harnessiq.providers.snovio.requests import (
    build_access_token_request,
    build_add_prospect_request,
    build_add_to_campaign_request,
    build_add_to_list_request,
    build_all_campaigns_params,
    build_campaign_data_params,
    build_campaign_recipient_status_params,
    build_campaign_recipients_params,
    build_delete_from_list_request,
    build_delete_prospect_request,
    build_domain_search_params,
    build_email_info_request,
    build_email_verifier_request,
    build_emails_count_params,
    build_emails_from_names_request,
    build_get_list_params,
    build_get_prospect_params,
    build_pause_campaign_request,
    build_profile_emails_request,
    build_prospect_lists_params,
    build_start_campaign_request,
    build_update_prospect_request,
    build_url_search_request,
    build_user_info_params,
)


@dataclass(frozen=True, slots=True)
class SnovioClient:
    """Minimal Snov.io API client.

    Args:
        client_id: Snov.io OAuth2 application client ID.
        client_secret: Snov.io OAuth2 application client secret.
        base_url: Override the default API base URL.
        timeout_seconds: Per-request timeout in seconds.
        request_executor: Pluggable HTTP executor for testing.
    """

    client_id: str
    client_secret: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 60.0
    request_executor: RequestExecutor = request_json

    # -------------------------------------------------------------------------
    # Authentication
    # -------------------------------------------------------------------------

    def get_access_token(self) -> Any:
        """Exchange client credentials for an OAuth2 access token."""
        body = build_access_token_request(self.client_id, self.client_secret)
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }
        return self.request_executor(
            "POST",
            access_token_url(self.base_url),
            headers=headers,
            json_body=None,
            timeout_seconds=self.timeout_seconds,
        )

    # -------------------------------------------------------------------------
    # Email discovery
    # -------------------------------------------------------------------------

    def domain_search(
        self,
        access_token: str,
        domain: str,
        *,
        type: str | None = None,
        limit: int | None = None,
        last_id: int | None = None,
    ) -> Any:
        """Search for emails associated with a domain."""
        params = build_domain_search_params(
            access_token, domain, type=type, limit=limit, last_id=last_id
        )
        return self._get(domain_search_url(self.base_url), params=params)

    def get_emails_count(
        self,
        access_token: str,
        domain: str,
        *,
        type: str | None = None,
    ) -> Any:
        """Count emails available for a domain."""
        params = build_emails_count_params(access_token, domain, type=type)
        return self._get(emails_count_url(self.base_url), params=params)

    def get_emails_from_names(
        self,
        access_token: str,
        first_name: str,
        last_name: str,
        domain: str,
    ) -> Any:
        """Find emails for a person by name and domain."""
        body = build_emails_from_names_request(access_token, first_name, last_name, domain)
        return self._post(emails_from_names_url(self.base_url), body=body)

    def get_email_info(self, access_token: str, email: str) -> Any:
        """Retrieve full information about a known email address."""
        body = build_email_info_request(access_token, email)
        return self._post(email_info_url(self.base_url), body=body)

    def verify_email(self, access_token: str, email: str) -> Any:
        """Verify email deliverability."""
        body = build_email_verifier_request(access_token, email)
        return self._post(email_verifier_url(self.base_url), body=body)

    def get_profile_emails(self, access_token: str, url: str) -> Any:
        """Retrieve emails associated with a social profile URL."""
        body = build_profile_emails_request(access_token, url)
        return self._post(profile_emails_url(self.base_url), body=body)

    def url_search(self, access_token: str, url: str) -> Any:
        """Find a prospect from a social profile URL."""
        body = build_url_search_request(access_token, url)
        return self._post(url_search_url(self.base_url), body=body)

    # -------------------------------------------------------------------------
    # Prospects
    # -------------------------------------------------------------------------

    def get_prospect(self, access_token: str, prospect_id: str) -> Any:
        """Retrieve a prospect by ID."""
        params = build_get_prospect_params(access_token, prospect_id)
        return self._get(prospect_url(self.base_url), params=params)

    def add_prospect(
        self,
        access_token: str,
        email: str,
        full_name: str,
        list_id: str,
        **kwargs: Any,
    ) -> Any:
        """Add a prospect to a list."""
        body = build_add_prospect_request(access_token, email, full_name, list_id, **kwargs)
        return self._post(add_prospect_url(self.base_url), body=body)

    def update_prospect(
        self,
        access_token: str,
        prospect_id: str,
        fields: dict[str, Any],
    ) -> Any:
        """Update fields on an existing prospect."""
        body = build_update_prospect_request(access_token, prospect_id, fields)
        return self._post(update_prospect_url(self.base_url), body=body)

    def delete_prospect(self, access_token: str, prospect_id: str) -> Any:
        """Delete a prospect by ID."""
        body = build_delete_prospect_request(access_token, prospect_id)
        return self._delete(delete_prospect_url(self.base_url), body=body)

    # -------------------------------------------------------------------------
    # Prospect lists
    # -------------------------------------------------------------------------

    def get_prospect_lists(self, access_token: str) -> Any:
        """Return all prospect lists for the account."""
        params = build_prospect_lists_params(access_token)
        return self._get(prospect_lists_url(self.base_url), params=params)

    def get_list(self, access_token: str, list_id: str) -> Any:
        """Return a specific prospect list by ID."""
        params = build_get_list_params(access_token, list_id)
        return self._get(get_list_url(self.base_url), params=params)

    def add_to_list(self, access_token: str, email: str, list_id: str) -> Any:
        """Add an email address to a prospect list."""
        body = build_add_to_list_request(access_token, email, list_id)
        return self._post(add_to_list_url(self.base_url), body=body)

    def delete_from_list(self, access_token: str, list_id: str, email: str) -> Any:
        """Remove an email address from a prospect list."""
        body = build_delete_from_list_request(access_token, list_id, email)
        return self._delete(delete_from_list_url(self.base_url), body=body)

    # -------------------------------------------------------------------------
    # Campaigns
    # -------------------------------------------------------------------------

    def get_all_campaigns(self, access_token: str) -> Any:
        """List all campaigns for the account."""
        params = build_all_campaigns_params(access_token)
        return self._get(all_campaigns_url(self.base_url), params=params)

    def get_campaign(self, access_token: str, campaign_id: str) -> Any:
        """Retrieve campaign details by ID."""
        params = build_campaign_data_params(access_token, campaign_id)
        return self._get(campaign_data_url(self.base_url), params=params)

    def get_campaign_recipients(
        self,
        access_token: str,
        campaign_id: str,
        *,
        status: str | None = None,
    ) -> Any:
        """List recipients for a campaign, optionally filtered by status."""
        params = build_campaign_recipients_params(access_token, campaign_id, status=status)
        return self._get(campaign_recipients_url(self.base_url), params=params)

    def get_campaign_recipient_status(
        self,
        access_token: str,
        email: str,
        campaign_id: str,
    ) -> Any:
        """Get the status of a specific recipient in a campaign."""
        params = build_campaign_recipient_status_params(access_token, email, campaign_id)
        return self._get(campaign_recipient_status_url(self.base_url), params=params)

    def add_to_campaign(
        self,
        access_token: str,
        campaign_id: str,
        emails: list[str],
    ) -> Any:
        """Add a list of email addresses to a campaign."""
        body = build_add_to_campaign_request(access_token, campaign_id, emails)
        return self._post(add_to_campaign_url(self.base_url), body=body)

    def start_campaign(self, access_token: str, campaign_id: str) -> Any:
        """Start a paused or newly created campaign."""
        body = build_start_campaign_request(access_token, campaign_id)
        return self._post(start_campaign_url(self.base_url), body=body)

    def pause_campaign(self, access_token: str, campaign_id: str) -> Any:
        """Pause a running campaign."""
        body = build_pause_campaign_request(access_token, campaign_id)
        return self._post(pause_campaign_url(self.base_url), body=body)

    # -------------------------------------------------------------------------
    # Account
    # -------------------------------------------------------------------------

    def get_user_info(self, access_token: str) -> Any:
        """Retrieve current user account information."""
        params = build_user_info_params(access_token)
        return self._get(user_info_url(self.base_url), params=params)

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _get(self, url: str, *, params: dict[str, object] | None = None) -> Any:
        full_url = url
        if params:
            full_url = f"{url}?{parse.urlencode(params)}"
        return self.request_executor(
            "GET",
            full_url,
            headers={"Accept": "application/json"},
            timeout_seconds=self.timeout_seconds,
        )

    def _post(self, url: str, *, body: dict[str, object] | None = None) -> Any:
        return self.request_executor(
            "POST",
            url,
            headers={"Accept": "application/json"},
            json_body=dict(body) if body is not None else None,
            timeout_seconds=self.timeout_seconds,
        )

    def _delete(self, url: str, *, body: dict[str, object] | None = None) -> Any:
        return self.request_executor(
            "DELETE",
            url,
            headers={"Accept": "application/json"},
            json_body=dict(body) if body is not None else None,
            timeout_seconds=self.timeout_seconds,
        )
