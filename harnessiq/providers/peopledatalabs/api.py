"""People Data Labs endpoint and authentication helpers."""

from __future__ import annotations

from typing import Mapping

from harnessiq.providers.http import join_url

DEFAULT_BASE_URL = "https://api.peopledatalabs.com/v5"


def build_headers(
    api_key: str,
    *,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build request headers for the People Data Labs API.

    PDL uses an ``X-Api-Key`` header for authentication.
    """
    headers: dict[str, str] = {"X-Api-Key": api_key}
    if extra_headers:
        headers.update(extra_headers)
    return headers


# ── Person endpoints ────────────────────────────────────────────────────────


def person_enrich_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the person enrichment URL."""
    return join_url(base_url, "/person/enrich")


def person_identify_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the person identify URL."""
    return join_url(base_url, "/person/identify")


def person_search_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the person search URL."""
    return join_url(base_url, "/person/search")


def person_bulk_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the person bulk enrich URL."""
    return join_url(base_url, "/person/bulk")


# ── Company endpoints ────────────────────────────────────────────────────────


def company_enrich_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the company enrichment URL."""
    return join_url(base_url, "/company/enrich")


def company_search_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the company search URL."""
    return join_url(base_url, "/company/search")


def company_bulk_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the company bulk enrich URL."""
    return join_url(base_url, "/company/bulk")


# ── School endpoints ─────────────────────────────────────────────────────────


def school_enrich_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the school enrichment URL."""
    return join_url(base_url, "/school/enrich")


# ── Location endpoints ────────────────────────────────────────────────────────


def location_clean_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the location clean URL."""
    return join_url(base_url, "/location/clean")


# ── Autocomplete endpoint ─────────────────────────────────────────────────────


def autocomplete_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the autocomplete URL."""
    return join_url(base_url, "/autocomplete")


# ── Job title endpoint ────────────────────────────────────────────────────────


def job_title_enrich_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the job title enrichment URL."""
    return join_url(base_url, "/job_title/enrich")
