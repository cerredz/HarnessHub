"""Thin Proxycurl API client wrapper.

NOTE: Proxycurl shut down in January 2025 following a LinkedIn lawsuit.
This client is preserved for reference only and will not produce live responses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from harnessiq.providers.proxycurl.api import (
    DEFAULT_BASE_URL,
    build_headers,
    get_personal_contacts_url,
    get_personal_emails_url,
    list_company_employees_url,
    list_company_jobs_url,
    resolve_company_linkedin_url,
    resolve_email_to_profile_url,
    resolve_person_linkedin_url,
    scrape_linkedin_company_url,
    scrape_linkedin_person_url,
    search_jobs_url,
    lookup_person_by_email_url,
)
from harnessiq.providers.proxycurl.requests import (
    build_list_company_jobs_params,
    build_list_employees_params,
    build_lookup_person_by_email_params,
    build_personal_contacts_params,
    build_personal_emails_params,
    build_resolve_company_params,
    build_resolve_email_params,
    build_resolve_person_params,
    build_scrape_company_params,
    build_scrape_person_params,
    build_search_jobs_params,
)
from harnessiq.providers.http import RequestExecutor, request_json


@dataclass(frozen=True, slots=True)
class ProxycurlClient:
    """Minimal Proxycurl API client covering all last-known public endpoints.

    NOTE: Proxycurl shut down in January 2025 following a LinkedIn lawsuit.
    This client is preserved for reference only.

    All methods issue GET requests with query parameters appended to the URL.
    """

    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 60.0
    request_executor: RequestExecutor = request_json

    # ── LinkedIn person methods ───────────────────────────────────────────────

    def scrape_person_profile(
        self,
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
    ) -> Any:
        """Scrape a LinkedIn person profile by URL."""
        params = build_scrape_person_params(
            url=url,
            fallback_to_cache=fallback_to_cache,
            use_cache=use_cache,
            skills=skills,
            inferred_salary=inferred_salary,
            personal_email=personal_email,
            personal_contact_number=personal_contact_number,
            twitter_profile_id=twitter_profile_id,
            facebook_profile_id=facebook_profile_id,
            github_profile_id=github_profile_id,
            extra=extra,
        )
        endpoint = scrape_linkedin_person_url(self.base_url, query=params)
        return self._get(endpoint)

    def resolve_person_profile(
        self,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        company_domain: str | None = None,
        similarity_checks: str | None = None,
        enrich_profile: str | None = None,
    ) -> Any:
        """Find the LinkedIn profile URL for a person by name / company domain."""
        params = build_resolve_person_params(
            first_name=first_name,
            last_name=last_name,
            company_domain=company_domain,
            similarity_checks=similarity_checks,
            enrich_profile=enrich_profile,
        )
        endpoint = resolve_person_linkedin_url(self.base_url, query=params)
        return self._get(endpoint)

    def lookup_person_by_email(
        self,
        *,
        email_address: str,
        lookup_depth: str | None = None,
        enrich_profile: str | None = None,
    ) -> Any:
        """Look up a LinkedIn profile by email address."""
        params = build_lookup_person_by_email_params(
            email_address=email_address,
            lookup_depth=lookup_depth,
            enrich_profile=enrich_profile,
        )
        endpoint = lookup_person_by_email_url(self.base_url, query=params)
        return self._get(endpoint)

    # ── LinkedIn company methods ──────────────────────────────────────────────

    def scrape_company_profile(
        self,
        *,
        url: str,
        categories: str | None = None,
        funding_data: str | None = None,
        extra: str | None = None,
        exit_data: str | None = None,
        acquisitions: str | None = None,
        use_cache: str | None = None,
    ) -> Any:
        """Scrape a LinkedIn company profile by URL."""
        params = build_scrape_company_params(
            url=url,
            categories=categories,
            funding_data=funding_data,
            extra=extra,
            exit_data=exit_data,
            acquisitions=acquisitions,
            use_cache=use_cache,
        )
        endpoint = scrape_linkedin_company_url(self.base_url, query=params)
        return self._get(endpoint)

    def resolve_company_profile(
        self,
        *,
        company_name: str | None = None,
        company_domain: str | None = None,
        company_location: str | None = None,
    ) -> Any:
        """Find the LinkedIn URL for a company by name / domain."""
        params = build_resolve_company_params(
            company_name=company_name,
            company_domain=company_domain,
            company_location=company_location,
        )
        endpoint = resolve_company_linkedin_url(self.base_url, query=params)
        return self._get(endpoint)

    def list_company_employees(
        self,
        *,
        url: str,
        country: str | None = None,
        enrich_profiles: str | None = None,
        role_search: str | None = None,
        page_size: int | None = None,
        employment_status: str | None = None,
        sort_by: str | None = None,
        resolve_numeric_id: str | None = None,
    ) -> Any:
        """List employees of a LinkedIn company."""
        params = build_list_employees_params(
            url=url,
            country=country,
            enrich_profiles=enrich_profiles,
            role_search=role_search,
            page_size=page_size,
            employment_status=employment_status,
            sort_by=sort_by,
            resolve_numeric_id=resolve_numeric_id,
        )
        endpoint = list_company_employees_url(self.base_url, query=params)
        return self._get(endpoint)

    # ── Job methods ───────────────────────────────────────────────────────────

    def list_company_jobs(
        self,
        *,
        url: str,
        keyword: str | None = None,
        search_id: str | None = None,
        type: str | None = None,
        experience_level: str | None = None,
        when: str | None = None,
        flexibility: str | None = None,
        geo_id: str | None = None,
    ) -> Any:
        """List job postings for a LinkedIn company."""
        params = build_list_company_jobs_params(
            url=url,
            keyword=keyword,
            search_id=search_id,
            type=type,
            experience_level=experience_level,
            when=when,
            flexibility=flexibility,
            geo_id=geo_id,
        )
        endpoint = list_company_jobs_url(self.base_url, query=params)
        return self._get(endpoint)

    def search_jobs(
        self,
        *,
        keyword: str | None = None,
        geo_id: str | None = None,
        type: str | None = None,
        experience_level: str | None = None,
        when: str | None = None,
        flexibility: str | None = None,
    ) -> Any:
        """Search LinkedIn job postings."""
        params = build_search_jobs_params(
            keyword=keyword,
            geo_id=geo_id,
            type=type,
            experience_level=experience_level,
            when=when,
            flexibility=flexibility,
        )
        endpoint = search_jobs_url(self.base_url, query=params)
        return self._get(endpoint)

    # ── Contact / email methods ───────────────────────────────────────────────

    def resolve_email_to_profile(self, *, email: str) -> Any:
        """Resolve an email address to a LinkedIn profile."""
        params = build_resolve_email_params(email=email)
        endpoint = resolve_email_to_profile_url(self.base_url, query=params)
        return self._get(endpoint)

    def get_personal_emails(
        self,
        *,
        linkedin_profile_url: str,
        page_size: int | None = None,
        invalid_email_removal: str | None = None,
    ) -> Any:
        """Retrieve personal email addresses for a LinkedIn profile."""
        params = build_personal_emails_params(
            linkedin_profile_url=linkedin_profile_url,
            page_size=page_size,
            invalid_email_removal=invalid_email_removal,
        )
        endpoint = get_personal_emails_url(self.base_url, query=params)
        return self._get(endpoint)

    def get_personal_contacts(
        self,
        *,
        linkedin_profile_url: str,
        page_size: int | None = None,
    ) -> Any:
        """Retrieve personal phone numbers for a LinkedIn profile."""
        params = build_personal_contacts_params(
            linkedin_profile_url=linkedin_profile_url,
            page_size=page_size,
        )
        endpoint = get_personal_contacts_url(self.base_url, query=params)
        return self._get(endpoint)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get(self, url: str) -> Any:
        return self.request_executor(
            "GET",
            url,
            headers=build_headers(self.api_key),
            json_body=None,
            timeout_seconds=self.timeout_seconds,
        )
