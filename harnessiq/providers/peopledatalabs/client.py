"""Thin People Data Labs API client wrapper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from harnessiq.providers.base import omit_none_values
from harnessiq.providers.http import RequestExecutor, request_json
from harnessiq.providers.peopledatalabs.api import (
    DEFAULT_BASE_URL,
    autocomplete_url,
    build_headers,
    company_bulk_url,
    company_enrich_url,
    company_search_url,
    job_title_enrich_url,
    location_clean_url,
    person_bulk_url,
    person_enrich_url,
    person_identify_url,
    person_search_url,
    school_enrich_url,
)
from harnessiq.providers.peopledatalabs.requests import (
    build_company_bulk_request,
    build_company_search_request,
    build_person_bulk_request,
    build_person_search_request,
)


def _append_query(url: str, params: dict[str, Any]) -> str:
    """Append *params* (omitting ``None`` values) to *url* as a query string."""
    filtered = omit_none_values(params)
    if not filtered:
        return url
    return f"{url}?{urlencode(filtered)}"


@dataclass(frozen=True, slots=True)
class PeopleDataLabsClient:
    """Minimal People Data Labs client that delegates to local request builders."""

    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 60.0
    request_executor: RequestExecutor = request_json

    # ── Person ────────────────────────────────────────────────────────────────

    def enrich_person(
        self,
        *,
        email: str | None = None,
        phone: str | None = None,
        name: str | None = None,
        linkedin_url: str | None = None,
        company: str | None = None,
        location: str | None = None,
        birth_date: str | None = None,
        profile: str | None = None,
        required: str | None = None,
        min_likelihood: int | None = None,
        pretty: bool | None = None,
    ) -> Any:
        """Enrich a person record using a GET request with query parameters."""
        url = _append_query(
            person_enrich_url(self.base_url),
            {
                "email": email,
                "phone": phone,
                "name": name,
                "linkedin_url": linkedin_url,
                "company": company,
                "location": location,
                "birth_date": birth_date,
                "profile": profile,
                "required": required,
                "min_likelihood": min_likelihood,
                "pretty": pretty,
            },
        )
        return self._request("GET", url)

    def identify_person(
        self,
        *,
        email: str | None = None,
        phone: str | None = None,
        name: str | None = None,
        linkedin_url: str | None = None,
        company: str | None = None,
        location: str | None = None,
        birth_date: str | None = None,
        profile: str | None = None,
        required: str | None = None,
        min_likelihood: int | None = None,
        pretty: bool | None = None,
    ) -> Any:
        """Identify a person using a GET request with query parameters."""
        url = _append_query(
            person_identify_url(self.base_url),
            {
                "email": email,
                "phone": phone,
                "name": name,
                "linkedin_url": linkedin_url,
                "company": company,
                "location": location,
                "birth_date": birth_date,
                "profile": profile,
                "required": required,
                "min_likelihood": min_likelihood,
                "pretty": pretty,
            },
        )
        return self._request("GET", url)

    def search_people(
        self,
        *,
        query: dict[str, Any] | None = None,
        sql: str | None = None,
        size: int = 10,
        from_: int = 0,
    ) -> Any:
        """Search people using a POST request with a JSON body."""
        payload = build_person_search_request(
            query=query,
            sql=sql,
            size=size,
            from_=from_,
        )
        return self._request("POST", person_search_url(self.base_url), json_body=payload)

    def bulk_enrich_people(
        self,
        requests: list[dict[str, Any]],
        *,
        size: int | None = None,
    ) -> Any:
        """Bulk enrich multiple person records using a POST request."""
        payload = build_person_bulk_request(requests, size=size)
        return self._request("POST", person_bulk_url(self.base_url), json_body=payload)

    # ── Company ───────────────────────────────────────────────────────────────

    def enrich_company(
        self,
        *,
        name: str | None = None,
        website: str | None = None,
        profile: str | None = None,
        ticker: str | None = None,
        pretty: bool | None = None,
    ) -> Any:
        """Enrich a company record using a GET request with query parameters."""
        url = _append_query(
            company_enrich_url(self.base_url),
            {
                "name": name,
                "website": website,
                "profile": profile,
                "ticker": ticker,
                "pretty": pretty,
            },
        )
        return self._request("GET", url)

    def search_companies(
        self,
        *,
        query: dict[str, Any] | None = None,
        sql: str | None = None,
        size: int = 10,
        from_: int = 0,
    ) -> Any:
        """Search companies using a POST request with a JSON body."""
        payload = build_company_search_request(
            query=query,
            sql=sql,
            size=size,
            from_=from_,
        )
        return self._request("POST", company_search_url(self.base_url), json_body=payload)

    def bulk_enrich_companies(
        self,
        requests: list[dict[str, Any]],
        *,
        size: int | None = None,
    ) -> Any:
        """Bulk enrich multiple company records using a POST request."""
        payload = build_company_bulk_request(requests, size=size)
        return self._request("POST", company_bulk_url(self.base_url), json_body=payload)

    # ── School ────────────────────────────────────────────────────────────────

    def enrich_school(
        self,
        *,
        name: str | None = None,
        website: str | None = None,
        profile: str | None = None,
        pretty: bool | None = None,
    ) -> Any:
        """Enrich a school record using a GET request with query parameters."""
        url = _append_query(
            school_enrich_url(self.base_url),
            {
                "name": name,
                "website": website,
                "profile": profile,
                "pretty": pretty,
            },
        )
        return self._request("GET", url)

    # ── Location ──────────────────────────────────────────────────────────────

    def clean_location(self, location: str, *, pretty: bool | None = None) -> Any:
        """Clean and normalize a location string using a GET request."""
        url = _append_query(
            location_clean_url(self.base_url),
            {"location": location, "pretty": pretty},
        )
        return self._request("GET", url)

    # ── Autocomplete ──────────────────────────────────────────────────────────

    def autocomplete(
        self,
        field: str,
        text: str,
        *,
        size: int = 10,
    ) -> Any:
        """Autocomplete field values using a GET request."""
        url = _append_query(
            autocomplete_url(self.base_url),
            {"field": field, "text": text, "size": size},
        )
        return self._request("GET", url)

    # ── Job title ─────────────────────────────────────────────────────────────

    def enrich_job_title(self, job_title: str, *, pretty: bool | None = None) -> Any:
        """Enrich and normalize a job title using a GET request."""
        url = _append_query(
            job_title_enrich_url(self.base_url),
            {"job_title": job_title, "pretty": pretty},
        )
        return self._request("GET", url)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _request(
        self,
        method: str,
        url: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        return self.request_executor(
            method,
            url,
            headers=build_headers(self.api_key),
            json_body=json_body,
            timeout_seconds=self.timeout_seconds,
        )
