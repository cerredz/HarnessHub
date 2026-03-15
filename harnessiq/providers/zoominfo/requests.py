"""ZoomInfo REST API request payload builders."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from harnessiq.providers.base import omit_none_values


def build_authenticate_request(username: str, password: str) -> dict[str, object]:
    """Build the authentication request body."""
    return {"username": username, "password": password}


def build_search_contact_request(
    *,
    output_fields: list[str],
    match_filter: dict[str, Any],
    rpp: int | None = None,
    page: int | None = None,
) -> dict[str, object]:
    """Build a contact search request body."""
    return omit_none_values(
        {
            "outputFields": list(output_fields),
            "matchFilter": deepcopy(match_filter),
            "rpp": rpp,
            "page": page,
        }
    )


def build_search_company_request(
    *,
    output_fields: list[str],
    match_filter: dict[str, Any],
    rpp: int | None = None,
    page: int | None = None,
) -> dict[str, object]:
    """Build a company search request body."""
    return omit_none_values(
        {
            "outputFields": list(output_fields),
            "matchFilter": deepcopy(match_filter),
            "rpp": rpp,
            "page": page,
        }
    )


def build_search_intent_request(
    *,
    company_ids: list[str | int],
    topics: list[str],
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, object]:
    """Build an intent data search request body."""
    return omit_none_values(
        {
            "companyIds": list(company_ids),
            "topics": list(topics),
            "startDate": start_date,
            "endDate": end_date,
        }
    )


def build_search_news_request(
    *,
    match_filter: dict[str, Any] | None = None,
    rpp: int | None = None,
    page: int | None = None,
) -> dict[str, object]:
    """Build a news signals search request body."""
    return omit_none_values(
        {
            "matchFilter": deepcopy(match_filter) if match_filter is not None else None,
            "rpp": rpp,
            "page": page,
        }
    )


def build_search_scoop_request(
    *,
    match_filter: dict[str, Any] | None = None,
    rpp: int | None = None,
    page: int | None = None,
) -> dict[str, object]:
    """Build a business scoops search request body."""
    return omit_none_values(
        {
            "matchFilter": deepcopy(match_filter) if match_filter is not None else None,
            "rpp": rpp,
            "page": page,
        }
    )


def build_enrich_contact_request(
    *,
    match_input: list[dict[str, Any]],
    output_fields: list[str] | None = None,
) -> dict[str, object]:
    """Build a contact enrichment request body."""
    return omit_none_values(
        {
            "matchInput": deepcopy(match_input),
            "outputFields": list(output_fields) if output_fields is not None else None,
        }
    )


def build_enrich_company_request(
    *,
    match_input: list[dict[str, Any]],
    output_fields: list[str] | None = None,
) -> dict[str, object]:
    """Build a company enrichment request body."""
    return omit_none_values(
        {
            "matchInput": deepcopy(match_input),
            "outputFields": list(output_fields) if output_fields is not None else None,
        }
    )


def build_enrich_ip_request(
    ip_address: str,
    *,
    output_fields: list[str] | None = None,
) -> dict[str, object]:
    """Build an IP enrichment request body."""
    return omit_none_values(
        {
            "ipAddress": ip_address,
            "outputFields": list(output_fields) if output_fields is not None else None,
        }
    )


def build_bulk_contact_request(
    *,
    match_input: list[dict[str, Any]],
    output_fields: list[str] | None = None,
) -> dict[str, object]:
    """Build a bulk contact enrichment request body."""
    return omit_none_values(
        {
            "matchInput": deepcopy(match_input),
            "outputFields": list(output_fields) if output_fields is not None else None,
        }
    )


def build_bulk_company_request(
    *,
    match_input: list[dict[str, Any]],
    output_fields: list[str] | None = None,
) -> dict[str, object]:
    """Build a bulk company enrichment request body."""
    return omit_none_values(
        {
            "matchInput": deepcopy(match_input),
            "outputFields": list(output_fields) if output_fields is not None else None,
        }
    )


def build_lookup_outputfields_request(entity: str) -> dict[str, object]:
    """Build a request to look up available output fields for an entity type."""
    return {"entity": entity}
