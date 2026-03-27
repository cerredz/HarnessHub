"""Thin Coresignal API client wrapper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from harnessiq.providers.coresignal.operations import get_coresignal_operation
from harnessiq.providers.coresignal.api import (
    DEFAULT_BASE_URL,
    build_headers,
    company_collect_url,
    company_es_dsl_url,
    company_filter_search_url,
    employee_collect_url,
    employee_es_dsl_url,
    employee_filter_search_url,
    job_collect_url,
    job_es_dsl_url,
    job_filter_search_url,
)
from harnessiq.providers.coresignal.requests import (
    build_company_filter_request,
    build_employee_filter_request,
    build_es_dsl_request,
    build_job_filter_request,
)
from harnessiq.providers.http import RequestExecutor, request_json
from harnessiq.shared.dtos import ProviderPayloadRequestDTO, ProviderPayloadResultDTO
from harnessiq.shared.provider_payloads import execute_payload_operation


@dataclass(frozen=True, slots=True)
class CoreSignalClient:
    """Minimal Coresignal API client covering employee, company, and job endpoints.

    Authentication uses the ``apikey`` header (lowercase), not ``Authorization``
    or ``X-Api-Key``.
    """

    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 60.0
    request_executor: RequestExecutor = request_json

    # ── Employee methods ──────────────────────────────────────────────────────

    def search_employees_by_filter(
        self,
        *,
        name: str | None = None,
        title: str | None = None,
        company_name: str | None = None,
        location: str | None = None,
        page: int = 1,
        size: int = 10,
    ) -> Any:
        """Search employees using filter parameters."""
        payload = build_employee_filter_request(
            name=name,
            title=title,
            company_name=company_name,
            location=location,
            page=page,
            size=size,
        )
        return self._post(employee_filter_search_url(self.base_url), payload)

    def get_employee(self, employee_id: str | int) -> Any:
        """Retrieve an employee record by ID."""
        return self._get(employee_collect_url(self.base_url, employee_id))

    def search_employees_es_dsl(
        self,
        query: dict[str, Any],
        *,
        size: int = 10,
        from_: int = 0,
    ) -> Any:
        """Search employees using an Elasticsearch DSL query."""
        payload = build_es_dsl_request(query, size=size, from_=from_)
        return self._post(employee_es_dsl_url(self.base_url), payload)

    # ── Company methods ───────────────────────────────────────────────────────

    def search_companies_by_filter(
        self,
        *,
        name: str | None = None,
        website: str | None = None,
        industry: str | None = None,
        country: str | None = None,
        page: int = 1,
        size: int = 10,
    ) -> Any:
        """Search companies using filter parameters."""
        payload = build_company_filter_request(
            name=name,
            website=website,
            industry=industry,
            country=country,
            page=page,
            size=size,
        )
        return self._post(company_filter_search_url(self.base_url), payload)

    def get_company(self, company_id: str | int) -> Any:
        """Retrieve a company record by ID."""
        return self._get(company_collect_url(self.base_url, company_id))

    def search_companies_es_dsl(
        self,
        query: dict[str, Any],
        *,
        size: int = 10,
        from_: int = 0,
    ) -> Any:
        """Search companies using an Elasticsearch DSL query."""
        payload = build_es_dsl_request(query, size=size, from_=from_)
        return self._post(company_es_dsl_url(self.base_url), payload)

    # ── Job methods ───────────────────────────────────────────────────────────

    def search_jobs_by_filter(
        self,
        *,
        title: str | None = None,
        company_name: str | None = None,
        location: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        page: int = 1,
        size: int = 10,
    ) -> Any:
        """Search job postings using filter parameters."""
        payload = build_job_filter_request(
            title=title,
            company_name=company_name,
            location=location,
            date_from=date_from,
            date_to=date_to,
            page=page,
            size=size,
        )
        return self._post(job_filter_search_url(self.base_url), payload)

    def get_job(self, job_id: str | int) -> Any:
        """Retrieve a job record by ID."""
        return self._get(job_collect_url(self.base_url, job_id))

    def search_jobs_es_dsl(
        self,
        query: dict[str, Any],
        *,
        size: int = 10,
        from_: int = 0,
    ) -> Any:
        """Search job postings using an Elasticsearch DSL query."""
        payload = build_es_dsl_request(query, size=size, from_=from_)
        return self._post(job_es_dsl_url(self.base_url), payload)

    def execute_operation(self, request: ProviderPayloadRequestDTO) -> ProviderPayloadResultDTO:
        """Execute one Coresignal operation from a DTO envelope."""

        get_coresignal_operation(request.operation)
        return execute_payload_operation(self, request)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _get(self, url: str) -> Any:
        return self.request_executor(
            "GET",
            url,
            headers=build_headers(self.api_key),
            json_body=None,
            timeout_seconds=self.timeout_seconds,
        )

    def _post(self, url: str, payload: dict[str, Any]) -> Any:
        return self.request_executor(
            "POST",
            url,
            headers=build_headers(self.api_key),
            json_body=payload,
            timeout_seconds=self.timeout_seconds,
        )
