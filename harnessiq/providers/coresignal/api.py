"""Coresignal endpoint constants and authentication helpers."""

from __future__ import annotations

from typing import Mapping

from harnessiq.providers.http import join_url

from harnessiq.shared.providers import CORESIGNAL_DEFAULT_BASE_URL as DEFAULT_BASE_URL


def build_headers(
    api_key: str,
    *,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build request headers for the Coresignal API.

    Coresignal uses ``apikey`` (lowercase) as the authentication header name â€”
    not ``Authorization`` and not ``X-Api-Key``.
    """
    headers: dict[str, str] = {"apikey": api_key}
    if extra_headers:
        headers.update(extra_headers)
    return headers


# â”€â”€ Employee endpoints â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def employee_filter_search_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the employee filter search URL (POST /employee_base/search/filter)."""
    return join_url(base_url, "/employee_base/search/filter")


def employee_collect_url(base_url: str = DEFAULT_BASE_URL, employee_id: str | int = "") -> str:
    """Return the employee collect URL (GET /employee_base/collect/{id})."""
    return join_url(base_url, f"/employee_base/collect/{employee_id}")


def employee_es_dsl_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the employee Elasticsearch DSL search URL (POST /employee_base/search/es_dsl)."""
    return join_url(base_url, "/employee_base/search/es_dsl")


# â”€â”€ Company endpoints â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def company_filter_search_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the company filter search URL (POST /company_base/search/filter)."""
    return join_url(base_url, "/company_base/search/filter")


def company_collect_url(base_url: str = DEFAULT_BASE_URL, company_id: str | int = "") -> str:
    """Return the company collect URL (GET /company_base/collect/{id})."""
    return join_url(base_url, f"/company_base/collect/{company_id}")


def company_es_dsl_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the company Elasticsearch DSL search URL (POST /company_base/search/es_dsl)."""
    return join_url(base_url, "/company_base/search/es_dsl")


# â”€â”€ Job endpoints â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def job_filter_search_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the job filter search URL (POST /job_base/search/filter)."""
    return join_url(base_url, "/job_base/search/filter")


def job_collect_url(base_url: str = DEFAULT_BASE_URL, job_id: str | int = "") -> str:
    """Return the job collect URL (GET /job_base/collect/{id})."""
    return join_url(base_url, f"/job_base/collect/{job_id}")


def job_es_dsl_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the job Elasticsearch DSL search URL (POST /job_base/search/es_dsl)."""
    return join_url(base_url, "/job_base/search/es_dsl")

