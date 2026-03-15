"""Proxycurl REST API request query-parameter builders."""

from __future__ import annotations

from harnessiq.providers.base import omit_none_values


# ── LinkedIn person request builders ─────────────────────────────────────────


def build_scrape_person_params(
    *,
    url: str,
    fallback_to_cache: str | None = None,
    use_cache: str | None = None,
    skills: str | None = None,
    inferred_salary: str | None = None,
    personal_email: str | None = None,
    personal_contact_number: str | None = None,
    twitter_profile_id: str | None = None,
    facebook_profile_id: str | None = None,
    github_profile_id: str | None = None,
    extra: str | None = None,
) -> dict[str, object]:
    """Build query parameters for the LinkedIn person profile scrape endpoint."""
    return omit_none_values(
        {
            "url": url,
            "fallback_to_cache": fallback_to_cache,
            "use_cache": use_cache,
            "skills": skills,
            "inferred_salary": inferred_salary,
            "personal_email": personal_email,
            "personal_contact_number": personal_contact_number,
            "twitter_profile_id": twitter_profile_id,
            "facebook_profile_id": facebook_profile_id,
            "github_profile_id": github_profile_id,
            "extra": extra,
        }
    )


def build_resolve_person_params(
    *,
    first_name: str | None = None,
    last_name: str | None = None,
    company_domain: str | None = None,
    similarity_checks: str | None = None,
    enrich_profile: str | None = None,
) -> dict[str, object]:
    """Build query parameters for the person LinkedIn URL resolver endpoint."""
    return omit_none_values(
        {
            "first_name": first_name,
            "last_name": last_name,
            "company_domain": company_domain,
            "similarity_checks": similarity_checks,
            "enrich_profile": enrich_profile,
        }
    )


def build_lookup_person_by_email_params(
    *,
    email_address: str,
    lookup_depth: str | None = None,
    enrich_profile: str | None = None,
) -> dict[str, object]:
    """Build query parameters for the person lookup by email endpoint."""
    return omit_none_values(
        {
            "email_address": email_address,
            "lookup_depth": lookup_depth,
            "enrich_profile": enrich_profile,
        }
    )


# ── LinkedIn company request builders ────────────────────────────────────────


def build_scrape_company_params(
    *,
    url: str,
    categories: str | None = None,
    funding_data: str | None = None,
    extra: str | None = None,
    exit_data: str | None = None,
    acquisitions: str | None = None,
    use_cache: str | None = None,
) -> dict[str, object]:
    """Build query parameters for the LinkedIn company profile scrape endpoint."""
    return omit_none_values(
        {
            "url": url,
            "categories": categories,
            "funding_data": funding_data,
            "extra": extra,
            "exit_data": exit_data,
            "acquisitions": acquisitions,
            "use_cache": use_cache,
        }
    )


def build_resolve_company_params(
    *,
    company_name: str | None = None,
    company_domain: str | None = None,
    company_location: str | None = None,
) -> dict[str, object]:
    """Build query parameters for the company LinkedIn URL resolver endpoint."""
    return omit_none_values(
        {
            "company_name": company_name,
            "company_domain": company_domain,
            "company_location": company_location,
        }
    )


def build_list_employees_params(
    *,
    url: str,
    country: str | None = None,
    enrich_profiles: str | None = None,
    role_search: str | None = None,
    page_size: int | None = None,
    employment_status: str | None = None,
    sort_by: str | None = None,
    resolve_numeric_id: str | None = None,
) -> dict[str, object]:
    """Build query parameters for the company employees list endpoint."""
    return omit_none_values(
        {
            "url": url,
            "country": country,
            "enrich_profiles": enrich_profiles,
            "role_search": role_search,
            "page_size": page_size,
            "employment_status": employment_status,
            "sort_by": sort_by,
            "resolve_numeric_id": resolve_numeric_id,
        }
    )


# ── Job request builders ──────────────────────────────────────────────────────


def build_list_company_jobs_params(
    *,
    url: str,
    keyword: str | None = None,
    search_id: str | None = None,
    type: str | None = None,
    experience_level: str | None = None,
    when: str | None = None,
    flexibility: str | None = None,
    geo_id: str | None = None,
) -> dict[str, object]:
    """Build query parameters for the company job postings list endpoint."""
    return omit_none_values(
        {
            "url": url,
            "keyword": keyword,
            "search_id": search_id,
            "type": type,
            "experience_level": experience_level,
            "when": when,
            "flexibility": flexibility,
            "geo_id": geo_id,
        }
    )


def build_search_jobs_params(
    *,
    keyword: str | None = None,
    geo_id: str | None = None,
    type: str | None = None,
    experience_level: str | None = None,
    when: str | None = None,
    flexibility: str | None = None,
) -> dict[str, object]:
    """Build query parameters for the job search endpoint."""
    return omit_none_values(
        {
            "keyword": keyword,
            "geo_id": geo_id,
            "type": type,
            "experience_level": experience_level,
            "when": when,
            "flexibility": flexibility,
        }
    )


# ── Contact / email request builders ─────────────────────────────────────────


def build_resolve_email_params(
    *,
    email: str,
) -> dict[str, object]:
    """Build query parameters for the email-to-profile resolver endpoint."""
    return {"email": email}


def build_personal_emails_params(
    *,
    linkedin_profile_url: str,
    page_size: int | None = None,
    invalid_email_removal: str | None = None,
) -> dict[str, object]:
    """Build query parameters for the personal emails endpoint."""
    return omit_none_values(
        {
            "linkedin_profile_url": linkedin_profile_url,
            "page_size": page_size,
            "invalid_email_removal": invalid_email_removal,
        }
    )


def build_personal_contacts_params(
    *,
    linkedin_profile_url: str,
    page_size: int | None = None,
) -> dict[str, object]:
    """Build query parameters for the personal phone numbers endpoint."""
    return omit_none_values(
        {
            "linkedin_profile_url": linkedin_profile_url,
            "page_size": page_size,
        }
    )
