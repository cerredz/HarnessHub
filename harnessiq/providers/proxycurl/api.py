"""Proxycurl endpoint constants and authentication helpers.

NOTE: Proxycurl shut down in January 2025 following a LinkedIn lawsuit.
This module documents the last-known public API specification and is
preserved for reference only. The base URL and all endpoints listed here
are no longer reachable.
"""

from __future__ import annotations

from typing import Any, Mapping

from harnessiq.providers.http import join_url

DEFAULT_BASE_URL = "https://nubela.co/proxycurl/api"


def build_headers(
    api_key: str,
    *,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build request headers for the Proxycurl API.

    Proxycurl authenticates via an ``Authorization: Bearer {api_key}`` header.
    """
    headers: dict[str, str] = {"Authorization": f"Bearer {api_key}"}
    if extra_headers:
        headers.update(extra_headers)
    return headers


# ── LinkedIn person endpoints ─────────────────────────────────────────────────


def scrape_linkedin_person_url(
    base_url: str = DEFAULT_BASE_URL,
    *,
    query: Mapping[str, Any] | None = None,
) -> str:
    """Return the LinkedIn person profile scrape URL (GET /v2/linkedin)."""
    return join_url(base_url, "/v2/linkedin", query=query)


def resolve_person_linkedin_url(
    base_url: str = DEFAULT_BASE_URL,
    *,
    query: Mapping[str, Any] | None = None,
) -> str:
    """Return the person LinkedIn profile resolver URL (GET /linkedin/person/resolve)."""
    return join_url(base_url, "/linkedin/person/resolve", query=query)


def lookup_person_by_email_url(
    base_url: str = DEFAULT_BASE_URL,
    *,
    query: Mapping[str, Any] | None = None,
) -> str:
    """Return the person lookup by email URL (GET /v2/linkedin/person/lookup)."""
    return join_url(base_url, "/v2/linkedin/person/lookup", query=query)


# ── LinkedIn company endpoints ────────────────────────────────────────────────


def scrape_linkedin_company_url(
    base_url: str = DEFAULT_BASE_URL,
    *,
    query: Mapping[str, Any] | None = None,
) -> str:
    """Return the LinkedIn company profile scrape URL (GET /linkedin/company)."""
    return join_url(base_url, "/linkedin/company", query=query)


def resolve_company_linkedin_url(
    base_url: str = DEFAULT_BASE_URL,
    *,
    query: Mapping[str, Any] | None = None,
) -> str:
    """Return the company LinkedIn URL resolver (GET /linkedin/company/resolve)."""
    return join_url(base_url, "/linkedin/company/resolve", query=query)


def list_company_employees_url(
    base_url: str = DEFAULT_BASE_URL,
    *,
    query: Mapping[str, Any] | None = None,
) -> str:
    """Return the company employees list URL (GET /linkedin/company/employees)."""
    return join_url(base_url, "/linkedin/company/employees", query=query)


# ── Job endpoints ─────────────────────────────────────────────────────────────


def list_company_jobs_url(
    base_url: str = DEFAULT_BASE_URL,
    *,
    query: Mapping[str, Any] | None = None,
) -> str:
    """Return the company job postings URL (GET /linkedin/company/job)."""
    return join_url(base_url, "/linkedin/company/job", query=query)


def search_jobs_url(
    base_url: str = DEFAULT_BASE_URL,
    *,
    query: Mapping[str, Any] | None = None,
) -> str:
    """Return the job search URL (GET /linkedin/jobs/search)."""
    return join_url(base_url, "/linkedin/jobs/search", query=query)


# ── Contact / email endpoints ─────────────────────────────────────────────────


def resolve_email_to_profile_url(
    base_url: str = DEFAULT_BASE_URL,
    *,
    query: Mapping[str, Any] | None = None,
) -> str:
    """Return the email-to-LinkedIn profile resolver URL (GET /linkedin/profile/email/resolve)."""
    return join_url(base_url, "/linkedin/profile/email/resolve", query=query)


def get_personal_emails_url(
    base_url: str = DEFAULT_BASE_URL,
    *,
    query: Mapping[str, Any] | None = None,
) -> str:
    """Return the personal emails URL (GET /contact-api/personal-email)."""
    return join_url(base_url, "/contact-api/personal-email", query=query)


def get_personal_contacts_url(
    base_url: str = DEFAULT_BASE_URL,
    *,
    query: Mapping[str, Any] | None = None,
) -> str:
    """Return the personal phone numbers URL (GET /contact-api/personal-contact)."""
    return join_url(base_url, "/contact-api/personal-contact", query=query)
