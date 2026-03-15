"""Coresignal REST API request body builders."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from harnessiq.providers.base import omit_none_values


# ── Employee request builders ─────────────────────────────────────────────────


def build_employee_filter_request(
    *,
    name: str | None = None,
    title: str | None = None,
    company_name: str | None = None,
    location: str | None = None,
    page: int = 1,
    size: int = 10,
) -> dict[str, object]:
    """Build a POST body for the employee filter search endpoint."""
    return omit_none_values(
        {
            "name": name,
            "title": title,
            "company_name": company_name,
            "location": location,
            "page": page,
            "size": size,
        }
    )


def build_es_dsl_request(
    query: dict[str, Any],
    *,
    size: int = 10,
    from_: int = 0,
) -> dict[str, object]:
    """Build a POST body for an Elasticsearch DSL search endpoint."""
    return {
        "query": deepcopy(query),
        "size": size,
        "from": from_,
    }


# ── Company request builders ──────────────────────────────────────────────────


def build_company_filter_request(
    *,
    name: str | None = None,
    website: str | None = None,
    industry: str | None = None,
    country: str | None = None,
    page: int = 1,
    size: int = 10,
) -> dict[str, object]:
    """Build a POST body for the company filter search endpoint."""
    return omit_none_values(
        {
            "name": name,
            "website": website,
            "industry": industry,
            "country": country,
            "page": page,
            "size": size,
        }
    )


# ── Job request builders ──────────────────────────────────────────────────────


def build_job_filter_request(
    *,
    title: str | None = None,
    company_name: str | None = None,
    location: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    size: int = 10,
) -> dict[str, object]:
    """Build a POST body for the job filter search endpoint."""
    return omit_none_values(
        {
            "title": title,
            "company_name": company_name,
            "location": location,
            "date_from": date_from,
            "date_to": date_to,
            "page": page,
            "size": size,
        }
    )
