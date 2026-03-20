"""LeadIQ GraphQL request payload builders.

LeadIQ exposes a single ``POST /graphql`` endpoint.  Each builder in this
module returns a ``dict`` with ``"query"`` and ``"variables"`` keys that
can be passed directly as the JSON body.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from harnessiq.providers.base import omit_none_values
from harnessiq.shared.leadiq import (
    LEADIQ_ADD_TAG_TO_CONTACT_MUTATION,
    LEADIQ_CAPTURE_LEADS_MUTATION,
    LEADIQ_ENRICH_CONTACT_MUTATION,
    LEADIQ_FIND_PERSON_BY_LINKEDIN_QUERY,
    LEADIQ_GET_CAPTURES_QUERY,
    LEADIQ_GET_CAPTURE_STATUS_QUERY,
    LEADIQ_GET_CONTACT_DETAILS_QUERY,
    LEADIQ_GET_TAGS_QUERY,
    LEADIQ_GET_TEAM_ACTIVITY_QUERY,
    LEADIQ_REMOVE_TAG_FROM_CONTACT_MUTATION,
    LEADIQ_SEARCH_COMPANIES_QUERY,
    LEADIQ_SEARCH_CONTACTS_QUERY,
)


# ---------------------------------------------------------------------------
# Request builders
# ---------------------------------------------------------------------------


def build_search_contacts_request(
    *,
    name: str | None = None,
    email: str | None = None,
    company: str | None = None,
    title: str | None = None,
    location: str | None = None,
    linkedin_url: str | None = None,
    page: int | None = None,
    per_page: int | None = None,
) -> dict[str, object]:
    """Build a GraphQL request to search contacts."""
    filter_vars = omit_none_values(
        {
            "name": name,
            "email": email,
            "company": company,
            "title": title,
            "location": location,
            "linkedinUrl": linkedin_url,
        }
    )
    variables: dict[str, object] = omit_none_values(
        {
            "filter": filter_vars if filter_vars else None,
            "page": page,
            "perPage": per_page,
        }
    )
    return {"query": LEADIQ_SEARCH_CONTACTS_QUERY, "variables": variables}


def build_search_companies_request(
    *,
    name: str | None = None,
    domain: str | None = None,
    industry: str | None = None,
    employee_count_min: int | None = None,
    employee_count_max: int | None = None,
    page: int | None = None,
    per_page: int | None = None,
) -> dict[str, object]:
    """Build a GraphQL request to search companies."""
    filter_vars = omit_none_values(
        {
            "name": name,
            "domain": domain,
            "industry": industry,
            "employeeCountMin": employee_count_min,
            "employeeCountMax": employee_count_max,
        }
    )
    variables: dict[str, object] = omit_none_values(
        {
            "filter": filter_vars if filter_vars else None,
            "page": page,
            "perPage": per_page,
        }
    )
    return {"query": LEADIQ_SEARCH_COMPANIES_QUERY, "variables": variables}


def build_find_person_by_linkedin_request(linkedin_url: str) -> dict[str, object]:
    """Build a GraphQL request to look up a person by LinkedIn URL."""
    return {
        "query": LEADIQ_FIND_PERSON_BY_LINKEDIN_QUERY,
        "variables": {"linkedinUrl": linkedin_url},
    }


def build_enrich_contact_request(contact_id: str) -> dict[str, object]:
    """Build a GraphQL mutation to enrich a contact."""
    return {
        "query": LEADIQ_ENRICH_CONTACT_MUTATION,
        "variables": {"contactId": contact_id},
    }


def build_capture_leads_request(contacts: list[dict[str, Any]]) -> dict[str, object]:
    """Build a GraphQL mutation to capture a batch of leads."""
    return {
        "query": LEADIQ_CAPTURE_LEADS_MUTATION,
        "variables": {"contacts": deepcopy(contacts)},
    }


def build_get_captures_request(
    *,
    page: int | None = None,
    per_page: int | None = None,
) -> dict[str, object]:
    """Build a GraphQL request to list previously captured leads."""
    return {
        "query": LEADIQ_GET_CAPTURES_QUERY,
        "variables": omit_none_values({"page": page, "perPage": per_page}),
    }


def build_get_contact_details_request(contact_id: str) -> dict[str, object]:
    """Build a GraphQL request to get full contact details."""
    return {
        "query": LEADIQ_GET_CONTACT_DETAILS_QUERY,
        "variables": {"contactId": contact_id},
    }


def build_get_capture_status_request(capture_id: str) -> dict[str, object]:
    """Build a GraphQL request to check the status of a capture operation."""
    return {
        "query": LEADIQ_GET_CAPTURE_STATUS_QUERY,
        "variables": {"captureId": capture_id},
    }


def build_get_team_activity_request(
    *,
    page: int | None = None,
    per_page: int | None = None,
) -> dict[str, object]:
    """Build a GraphQL request to retrieve team activity."""
    return {
        "query": LEADIQ_GET_TEAM_ACTIVITY_QUERY,
        "variables": omit_none_values({"page": page, "perPage": per_page}),
    }


def build_get_tags_request() -> dict[str, object]:
    """Build a GraphQL request to list workspace tags."""
    return {"query": LEADIQ_GET_TAGS_QUERY, "variables": {}}


def build_add_tag_to_contact_request(
    contact_id: str,
    tag_id: str,
) -> dict[str, object]:
    """Build a GraphQL mutation to apply a tag to a contact."""
    return {
        "query": LEADIQ_ADD_TAG_TO_CONTACT_MUTATION,
        "variables": {"contactId": contact_id, "tagId": tag_id},
    }


def build_remove_tag_from_contact_request(
    contact_id: str,
    tag_id: str,
) -> dict[str, object]:
    """Build a GraphQL mutation to remove a tag from a contact."""
    return {
        "query": LEADIQ_REMOVE_TAG_FROM_CONTACT_MUTATION,
        "variables": {"contactId": contact_id, "tagId": tag_id},
    }
