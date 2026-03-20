"""ZoomInfo endpoint and authentication helpers."""

from __future__ import annotations

from typing import Mapping

from harnessiq.providers.base import omit_none_values
from harnessiq.providers.http import join_url

from harnessiq.shared.providers import ZOOMINFO_DEFAULT_BASE_URL as DEFAULT_BASE_URL


def build_auth_headers(
    *,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build headers for the unauthenticated /authenticate endpoint."""
    headers: dict[str, str] = {}
    if extra_headers:
        headers.update(extra_headers)
    return headers


def build_headers(
    jwt: str,
    *,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build headers for authenticated ZoomInfo API requests."""
    headers = omit_none_values({"Authorization": f"Bearer {jwt}"})
    if extra_headers:
        headers.update(extra_headers)
    return headers


def authenticate_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the authentication URL."""
    return join_url(base_url, "/authenticate")


def search_contact_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the contact search URL."""
    return join_url(base_url, "/search/contact")


def search_company_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the company search URL."""
    return join_url(base_url, "/search/company")


def search_intent_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the intent data search URL."""
    return join_url(base_url, "/search/intent")


def search_news_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the news signals search URL."""
    return join_url(base_url, "/search/news")


def search_scoop_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the business scoops search URL."""
    return join_url(base_url, "/search/scoop")


def enrich_contact_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the contact enrichment URL."""
    return join_url(base_url, "/enrich/contact")


def enrich_company_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the company enrichment URL."""
    return join_url(base_url, "/enrich/company")


def enrich_ip_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the IP enrichment URL."""
    return join_url(base_url, "/enrich/ip")


def bulk_contact_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the bulk contact enrichment URL."""
    return join_url(base_url, "/bulk/contact")


def bulk_company_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the bulk company enrichment URL."""
    return join_url(base_url, "/bulk/company")


def lookup_outputfields_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the output fields lookup URL."""
    return join_url(base_url, "/lookup/outputfields")


def usage_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the API usage stats URL."""
    return join_url(base_url, "/usage")

