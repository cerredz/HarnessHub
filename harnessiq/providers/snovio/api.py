"""Snov.io endpoint and authentication helpers."""

from __future__ import annotations

from harnessiq.providers.http import join_url

from harnessiq.shared.providers import SNOVIO_DEFAULT_BASE_URL as DEFAULT_BASE_URL


def access_token_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the OAuth2 token exchange URL."""
    return join_url(base_url, "/v1/oauth/access_token")


def domain_search_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the domain email search URL."""
    return join_url(base_url, "/v1/get-domain-search")


def emails_count_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the emails count URL."""
    return join_url(base_url, "/v1/get-emails-count")


def emails_from_names_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the emails-from-names URL."""
    return join_url(base_url, "/v1/get-emails-from-names")


def email_info_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the email info URL."""
    return join_url(base_url, "/v1/get-email-info")


def email_verifier_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the email verifier URL."""
    return join_url(base_url, "/v1/email-verifier")


def profile_emails_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the profile emails URL."""
    return join_url(base_url, "/v1/get-profile-emails")


def url_search_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the URL search URL."""
    return join_url(base_url, "/v1/url-search")


def prospect_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the get/delete prospect URL."""
    return join_url(base_url, "/v1/get-prospect")


def add_prospect_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the add prospect URL."""
    return join_url(base_url, "/v1/add-prospect")


def update_prospect_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the update prospect URL."""
    return join_url(base_url, "/v1/update-prospect")


def delete_prospect_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the delete prospect URL."""
    return join_url(base_url, "/v1/delete-prospect")


def prospect_lists_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the prospect lists URL."""
    return join_url(base_url, "/v1/prospect-list")


def get_list_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the get specific list URL."""
    return join_url(base_url, "/v1/get-list")


def add_to_list_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the add-to-list URL."""
    return join_url(base_url, "/v1/add-to-list")


def delete_from_list_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the delete-from-list URL."""
    return join_url(base_url, "/v1/delete-from-list")


def all_campaigns_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the all-campaigns URL."""
    return join_url(base_url, "/v1/get-all-campaigns")


def campaign_data_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the campaign data URL."""
    return join_url(base_url, "/v1/get-campaign-data")


def campaign_recipients_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the campaign recipients URL."""
    return join_url(base_url, "/v1/get-campaign-recipients")


def campaign_recipient_status_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the campaign recipient status URL."""
    return join_url(base_url, "/v1/get-campaign-recipient-status")


def add_to_campaign_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the add-to-campaign URL."""
    return join_url(base_url, "/v1/add-to-campaign")


def start_campaign_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the start campaign URL."""
    return join_url(base_url, "/v1/start-campaign")


def pause_campaign_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the pause campaign URL."""
    return join_url(base_url, "/v1/pause-campaign")


def user_info_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the user info URL (v2)."""
    return join_url(base_url, "/v2/me")

