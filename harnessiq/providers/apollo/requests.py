"""Apollo REST API request payload builders."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from harnessiq.providers.base import omit_none_values


def build_search_people_request(payload: dict[str, Any]) -> dict[str, object]:
    """Build a people-search request body."""
    return deepcopy(payload)


def build_search_organizations_request(payload: dict[str, Any]) -> dict[str, object]:
    """Build an organization-search request body."""
    return deepcopy(payload)


def build_enrich_person_request(payload: dict[str, Any]) -> dict[str, object]:
    """Build a single-person enrichment request body."""
    return deepcopy(payload)


def build_bulk_enrich_people_request(payload: dict[str, Any]) -> dict[str, object]:
    """Build a bulk people-enrichment request body."""
    return deepcopy(payload)


def build_enrich_organization_query(query: dict[str, Any]) -> dict[str, str | int | float | bool]:
    """Build organization-enrichment query parameters."""
    normalized = omit_none_values(deepcopy(query))
    return {str(key): value for key, value in normalized.items()}


def build_bulk_enrich_organizations_request(payload: dict[str, Any]) -> dict[str, object]:
    """Build a bulk organization-enrichment request body."""
    return deepcopy(payload)


def build_create_contact_request(payload: dict[str, Any]) -> dict[str, object]:
    """Build a contact-creation request body."""
    return deepcopy(payload)


def build_search_contacts_request(payload: dict[str, Any] | None = None) -> dict[str, object]:
    """Build a contact-search request body."""
    return deepcopy(payload or {})


def build_update_contact_request(payload: dict[str, Any]) -> dict[str, object]:
    """Build a contact-update request body."""
    return deepcopy(payload)


def build_search_sequences_request(payload: dict[str, Any] | None = None) -> dict[str, object]:
    """Build a sequence-search request body."""
    return deepcopy(payload or {})


def build_add_contacts_to_sequence_request(payload: dict[str, Any]) -> dict[str, object]:
    """Build an add-contacts-to-sequence request body."""
    return deepcopy(payload)


def build_usage_stats_request(payload: dict[str, Any] | None = None) -> dict[str, object]:
    """Build a usage-stats request body."""
    return deepcopy(payload or {})


__all__ = [
    "build_add_contacts_to_sequence_request",
    "build_bulk_enrich_organizations_request",
    "build_bulk_enrich_people_request",
    "build_create_contact_request",
    "build_enrich_organization_query",
    "build_enrich_person_request",
    "build_search_contacts_request",
    "build_search_organizations_request",
    "build_search_people_request",
    "build_search_sequences_request",
    "build_update_contact_request",
    "build_usage_stats_request",
]
