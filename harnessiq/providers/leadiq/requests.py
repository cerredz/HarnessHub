"""LeadIQ GraphQL request payload builders.

LeadIQ exposes a single ``POST /graphql`` endpoint.  Each builder in this
module returns a ``dict`` with ``"query"`` and ``"variables"`` keys that
can be passed directly as the JSON body.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from harnessiq.providers.base import omit_none_values

# ---------------------------------------------------------------------------
# Query documents
# ---------------------------------------------------------------------------

_SEARCH_CONTACTS_QUERY = """
query SearchContacts($filter: ContactFilter, $page: Int, $perPage: Int) {
  searchContacts(filter: $filter, page: $page, perPage: $perPage) {
    totalCount
    items {
      id
      firstName
      lastName
      title
      emails { email }
      phones { number }
      company { name domain }
      linkedinUrl
    }
  }
}
""".strip()

_SEARCH_COMPANIES_QUERY = """
query SearchCompanies($filter: CompanyFilter, $page: Int, $perPage: Int) {
  searchCompanies(filter: $filter, page: $page, perPage: $perPage) {
    totalCount
    items {
      id
      name
      domain
      industry
      employeeCount
      linkedinUrl
    }
  }
}
""".strip()

_FIND_PERSON_BY_LINKEDIN_QUERY = """
query FindPersonByLinkedIn($linkedinUrl: String!) {
  findPersonByLinkedIn(linkedinUrl: $linkedinUrl) {
    id
    firstName
    lastName
    title
    emails { email }
    phones { number }
    company { name domain }
  }
}
""".strip()

_ENRICH_CONTACT_MUTATION = """
mutation EnrichContact($contactId: ID!) {
  enrichContact(contactId: $contactId) {
    id
    emails { email status }
    phones { number type }
  }
}
""".strip()

_CAPTURE_LEADS_MUTATION = """
mutation CaptureLeads($contacts: [ContactInput!]!) {
  captureLeads(contacts: $contacts) {
    id
    status
    contact {
      id
      firstName
      lastName
    }
  }
}
""".strip()

_GET_CAPTURES_QUERY = """
query GetCaptures($page: Int, $perPage: Int) {
  getCaptures(page: $page, perPage: $perPage) {
    totalCount
    items {
      id
      status
      createdAt
      contact { id firstName lastName }
    }
  }
}
""".strip()

_GET_CONTACT_DETAILS_QUERY = """
query GetContactDetails($contactId: ID!) {
  getContactDetails(contactId: $contactId) {
    id
    firstName
    lastName
    title
    emails { email status }
    phones { number type }
    company { name domain industry }
    linkedinUrl
    location
  }
}
""".strip()

_GET_CAPTURE_STATUS_QUERY = """
query GetCaptureStatus($captureId: ID!) {
  getCaptureStatus(captureId: $captureId) {
    id
    status
    completedAt
    contact { id firstName lastName }
  }
}
""".strip()

_GET_TEAM_ACTIVITY_QUERY = """
query GetTeamActivity($page: Int, $perPage: Int) {
  getTeamActivity(page: $page, perPage: $perPage) {
    totalCount
    items {
      id
      action
      createdAt
      user { id name }
      contact { id firstName lastName }
    }
  }
}
""".strip()

_GET_TAGS_QUERY = """
query GetTags {
  getTags {
    id
    name
    color
    contactCount
  }
}
""".strip()

_ADD_TAG_TO_CONTACT_MUTATION = """
mutation AddTagToContact($contactId: ID!, $tagId: ID!) {
  addTagToContact(contactId: $contactId, tagId: $tagId) {
    id
    tags { id name }
  }
}
""".strip()

_REMOVE_TAG_FROM_CONTACT_MUTATION = """
mutation RemoveTagFromContact($contactId: ID!, $tagId: ID!) {
  removeTagFromContact(contactId: $contactId, tagId: $tagId) {
    id
    tags { id name }
  }
}
""".strip()


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
    return {"query": _SEARCH_CONTACTS_QUERY, "variables": variables}


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
    return {"query": _SEARCH_COMPANIES_QUERY, "variables": variables}


def build_find_person_by_linkedin_request(linkedin_url: str) -> dict[str, object]:
    """Build a GraphQL request to look up a person by LinkedIn URL."""
    return {
        "query": _FIND_PERSON_BY_LINKEDIN_QUERY,
        "variables": {"linkedinUrl": linkedin_url},
    }


def build_enrich_contact_request(contact_id: str) -> dict[str, object]:
    """Build a GraphQL mutation to enrich a contact."""
    return {
        "query": _ENRICH_CONTACT_MUTATION,
        "variables": {"contactId": contact_id},
    }


def build_capture_leads_request(contacts: list[dict[str, Any]]) -> dict[str, object]:
    """Build a GraphQL mutation to capture a batch of leads."""
    return {
        "query": _CAPTURE_LEADS_MUTATION,
        "variables": {"contacts": deepcopy(contacts)},
    }


def build_get_captures_request(
    *,
    page: int | None = None,
    per_page: int | None = None,
) -> dict[str, object]:
    """Build a GraphQL request to list previously captured leads."""
    return {
        "query": _GET_CAPTURES_QUERY,
        "variables": omit_none_values({"page": page, "perPage": per_page}),
    }


def build_get_contact_details_request(contact_id: str) -> dict[str, object]:
    """Build a GraphQL request to get full contact details."""
    return {
        "query": _GET_CONTACT_DETAILS_QUERY,
        "variables": {"contactId": contact_id},
    }


def build_get_capture_status_request(capture_id: str) -> dict[str, object]:
    """Build a GraphQL request to check the status of a capture operation."""
    return {
        "query": _GET_CAPTURE_STATUS_QUERY,
        "variables": {"captureId": capture_id},
    }


def build_get_team_activity_request(
    *,
    page: int | None = None,
    per_page: int | None = None,
) -> dict[str, object]:
    """Build a GraphQL request to retrieve team activity."""
    return {
        "query": _GET_TEAM_ACTIVITY_QUERY,
        "variables": omit_none_values({"page": page, "perPage": per_page}),
    }


def build_get_tags_request() -> dict[str, object]:
    """Build a GraphQL request to list workspace tags."""
    return {"query": _GET_TAGS_QUERY, "variables": {}}


def build_add_tag_to_contact_request(
    contact_id: str,
    tag_id: str,
) -> dict[str, object]:
    """Build a GraphQL mutation to apply a tag to a contact."""
    return {
        "query": _ADD_TAG_TO_CONTACT_MUTATION,
        "variables": {"contactId": contact_id, "tagId": tag_id},
    }


def build_remove_tag_from_contact_request(
    contact_id: str,
    tag_id: str,
) -> dict[str, object]:
    """Build a GraphQL mutation to remove a tag from a contact."""
    return {
        "query": _REMOVE_TAG_FROM_CONTACT_MUTATION,
        "variables": {"contactId": contact_id, "tagId": tag_id},
    }
