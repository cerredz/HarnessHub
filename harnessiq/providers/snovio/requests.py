"""Snov.io request payload builders."""

from __future__ import annotations

from copy import deepcopy
from typing import Any
from urllib import parse

from harnessiq.providers.base import omit_none_values


def build_access_token_request(client_id: str, client_secret: str) -> str:
    """Build a URL-encoded form body for the OAuth2 token exchange.

    Snov.io's token endpoint expects ``application/x-www-form-urlencoded``
    data, not JSON, so this function returns an encoded string rather than a
    dict.
    """
    return parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
    )


def build_domain_search_params(
    access_token: str,
    domain: str,
    *,
    type: str | None = None,
    limit: int | None = None,
    last_id: int | None = None,
) -> dict[str, object]:
    """Build query params for the domain email search endpoint."""
    return omit_none_values(
        {
            "access_token": access_token,
            "domain": domain,
            "type": type,
            "limit": limit,
            "lastId": last_id,
        }
    )


def build_emails_count_params(
    access_token: str,
    domain: str,
    *,
    type: str | None = None,
) -> dict[str, object]:
    """Build query params for the emails count endpoint."""
    return omit_none_values(
        {
            "access_token": access_token,
            "domain": domain,
            "type": type,
        }
    )


def build_emails_from_names_request(
    access_token: str,
    first_name: str,
    last_name: str,
    domain: str,
) -> dict[str, object]:
    """Build a POST body for the emails-from-names endpoint."""
    return {
        "access_token": access_token,
        "firstName": first_name,
        "lastName": last_name,
        "domain": domain,
    }


def build_email_info_request(
    access_token: str,
    email: str,
) -> dict[str, object]:
    """Build a POST body for the email info endpoint."""
    return {
        "access_token": access_token,
        "email": email,
    }


def build_email_verifier_request(
    access_token: str,
    email: str,
) -> dict[str, object]:
    """Build a POST body for the email verifier endpoint."""
    return {
        "access_token": access_token,
        "email": email,
    }


def build_profile_emails_request(
    access_token: str,
    url: str,
) -> dict[str, object]:
    """Build a POST body for the profile-emails endpoint."""
    return {
        "access_token": access_token,
        "url": url,
    }


def build_url_search_request(
    access_token: str,
    url: str,
) -> dict[str, object]:
    """Build a POST body for the URL search endpoint."""
    return {
        "access_token": access_token,
        "url": url,
    }


def build_get_prospect_params(
    access_token: str,
    prospect_id: str,
) -> dict[str, object]:
    """Build query params for the get-prospect endpoint."""
    return {
        "access_token": access_token,
        "id": prospect_id,
    }


def build_add_prospect_request(
    access_token: str,
    email: str,
    full_name: str,
    list_id: str,
    *,
    first_name: str | None = None,
    last_name: str | None = None,
    company_name: str | None = None,
    job_title: str | None = None,
    phone: str | None = None,
    linkedin_url: str | None = None,
    country: str | None = None,
    city: str | None = None,
    custom_fields: dict[str, Any] | None = None,
) -> dict[str, object]:
    """Build a POST body for the add-prospect endpoint."""
    return omit_none_values(
        {
            "access_token": access_token,
            "email": email,
            "fullName": full_name,
            "listId": list_id,
            "firstName": first_name,
            "lastName": last_name,
            "companyName": company_name,
            "jobTitle": job_title,
            "phone": phone,
            "linkedInUrl": linkedin_url,
            "country": country,
            "city": city,
            "customFields": deepcopy(custom_fields) if custom_fields is not None else None,
        }
    )


def build_update_prospect_request(
    access_token: str,
    prospect_id: str,
    fields: dict[str, Any],
) -> dict[str, object]:
    """Build a POST body for the update-prospect endpoint."""
    return {
        "access_token": access_token,
        "id": prospect_id,
        **deepcopy(fields),
    }


def build_delete_prospect_request(
    access_token: str,
    prospect_id: str,
) -> dict[str, object]:
    """Build a DELETE body for the delete-prospect endpoint."""
    return {
        "access_token": access_token,
        "id": prospect_id,
    }


def build_prospect_lists_params(access_token: str) -> dict[str, object]:
    """Build query params for the prospect-lists endpoint."""
    return {"access_token": access_token}


def build_get_list_params(
    access_token: str,
    list_id: str,
) -> dict[str, object]:
    """Build query params for the get-list endpoint."""
    return {
        "access_token": access_token,
        "listId": list_id,
    }


def build_add_to_list_request(
    access_token: str,
    email: str,
    list_id: str,
) -> dict[str, object]:
    """Build a POST body for the add-to-list endpoint."""
    return {
        "access_token": access_token,
        "email": email,
        "listId": list_id,
    }


def build_delete_from_list_request(
    access_token: str,
    list_id: str,
    email: str,
) -> dict[str, object]:
    """Build a DELETE body for the delete-from-list endpoint."""
    return {
        "access_token": access_token,
        "listId": list_id,
        "email": email,
    }


def build_all_campaigns_params(access_token: str) -> dict[str, object]:
    """Build query params for the all-campaigns endpoint."""
    return {"access_token": access_token}


def build_campaign_data_params(
    access_token: str,
    campaign_id: str,
) -> dict[str, object]:
    """Build query params for the campaign-data endpoint."""
    return {
        "access_token": access_token,
        "id": campaign_id,
    }


def build_campaign_recipients_params(
    access_token: str,
    campaign_id: str,
    *,
    status: str | None = None,
) -> dict[str, object]:
    """Build query params for the campaign-recipients endpoint."""
    return omit_none_values(
        {
            "access_token": access_token,
            "id": campaign_id,
            "status": status,
        }
    )


def build_campaign_recipient_status_params(
    access_token: str,
    email: str,
    campaign_id: str,
) -> dict[str, object]:
    """Build query params for the campaign-recipient-status endpoint."""
    return {
        "access_token": access_token,
        "email": email,
        "campaignId": campaign_id,
    }


def build_add_to_campaign_request(
    access_token: str,
    campaign_id: str,
    emails: list[str],
) -> dict[str, object]:
    """Build a POST body for the add-to-campaign endpoint."""
    return {
        "access_token": access_token,
        "id": campaign_id,
        "emails": list(emails),
    }


def build_start_campaign_request(
    access_token: str,
    campaign_id: str,
) -> dict[str, object]:
    """Build a POST body for the start-campaign endpoint."""
    return {
        "access_token": access_token,
        "id": campaign_id,
    }


def build_pause_campaign_request(
    access_token: str,
    campaign_id: str,
) -> dict[str, object]:
    """Build a POST body for the pause-campaign endpoint."""
    return {
        "access_token": access_token,
        "id": campaign_id,
    }


def build_user_info_params(access_token: str) -> dict[str, object]:
    """Build query params for the user-info endpoint."""
    return {"access_token": access_token}
