"""ZoomInfo API client with two-step JWT authentication."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from harnessiq.providers.zoominfo.operations import get_zoominfo_operation
from harnessiq.providers.zoominfo.api import (
    DEFAULT_BASE_URL,
    authenticate_url,
    build_headers,
    enrich_company_url,
    enrich_contact_url,
    enrich_ip_url,
    lookup_outputfields_url,
    search_company_url,
    search_contact_url,
    search_intent_url,
    search_news_url,
    search_scoop_url,
    usage_url,
)
from harnessiq.providers.zoominfo.requests import (
    build_authenticate_request,
    build_bulk_company_request,
    build_bulk_contact_request,
    build_enrich_company_request,
    build_enrich_contact_request,
    build_enrich_ip_request,
    build_search_company_request,
    build_search_contact_request,
    build_search_intent_request,
    build_search_news_request,
    build_search_scoop_request,
)
from harnessiq.providers.http import RequestExecutor, request_json
from harnessiq.shared.dtos import ProviderPayloadRequestDTO, ProviderPayloadResultDTO
from harnessiq.shared.provider_payloads import execute_payload_operation


@dataclass(frozen=True, slots=True)
class ZoomInfoClient:
    """Minimal ZoomInfo client with two-step JWT authentication.

    Usage::

        client = ZoomInfoClient(username="user@example.com", password="secret")
        jwt = client.authenticate()
        contacts = client.search_contacts(jwt, output_fields=["firstName"], match_filter={...})
    """

    username: str
    password: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 60.0
    request_executor: RequestExecutor = request_json

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def authenticate(self) -> str:
        """Obtain a JWT by posting credentials to /authenticate.

        Returns the raw JWT string that must be passed to all other methods.
        """
        payload = build_authenticate_request(self.username, self.password)
        response = self.request_executor(
            "POST",
            authenticate_url(self.base_url),
            headers={},
            json_body=payload,
            timeout_seconds=self.timeout_seconds,
        )
        return response["jwt"]

    # ------------------------------------------------------------------
    # Contact search
    # ------------------------------------------------------------------

    def search_contacts(
        self,
        jwt: str,
        *,
        output_fields: list[str],
        match_filter: dict[str, Any],
        rpp: int | None = None,
        page: int | None = None,
    ) -> Any:
        """Search for contacts matching the given filter criteria."""
        payload = build_search_contact_request(
            output_fields=output_fields,
            match_filter=match_filter,
            rpp=rpp,
            page=page,
        )
        return self._request(jwt, "POST", search_contact_url(self.base_url), json_body=payload)

    # ------------------------------------------------------------------
    # Company search
    # ------------------------------------------------------------------

    def search_companies(
        self,
        jwt: str,
        *,
        output_fields: list[str],
        match_filter: dict[str, Any],
        rpp: int | None = None,
        page: int | None = None,
    ) -> Any:
        """Search for companies matching the given filter criteria."""
        payload = build_search_company_request(
            output_fields=output_fields,
            match_filter=match_filter,
            rpp=rpp,
            page=page,
        )
        return self._request(jwt, "POST", search_company_url(self.base_url), json_body=payload)

    # ------------------------------------------------------------------
    # Intent data
    # ------------------------------------------------------------------

    def search_intent(
        self,
        jwt: str,
        *,
        company_ids: list[str | int],
        topics: list[str],
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> Any:
        """Search intent signals for a list of company IDs and topics."""
        payload = build_search_intent_request(
            company_ids=company_ids,
            topics=topics,
            start_date=start_date,
            end_date=end_date,
        )
        return self._request(jwt, "POST", search_intent_url(self.base_url), json_body=payload)

    # ------------------------------------------------------------------
    # News & scoops
    # ------------------------------------------------------------------

    def search_news(
        self,
        jwt: str,
        *,
        match_filter: dict[str, Any] | None = None,
        rpp: int | None = None,
        page: int | None = None,
    ) -> Any:
        """Search news signals."""
        payload = build_search_news_request(
            match_filter=match_filter,
            rpp=rpp,
            page=page,
        )
        return self._request(jwt, "POST", search_news_url(self.base_url), json_body=payload)

    def search_scoops(
        self,
        jwt: str,
        *,
        match_filter: dict[str, Any] | None = None,
        rpp: int | None = None,
        page: int | None = None,
    ) -> Any:
        """Search business scoops."""
        payload = build_search_scoop_request(
            match_filter=match_filter,
            rpp=rpp,
            page=page,
        )
        return self._request(jwt, "POST", search_scoop_url(self.base_url), json_body=payload)

    # ------------------------------------------------------------------
    # Enrichment
    # ------------------------------------------------------------------

    def enrich_contact(
        self,
        jwt: str,
        *,
        match_input: list[dict[str, Any]],
        output_fields: list[str] | None = None,
    ) -> Any:
        """Enrich contact data for one or more persons."""
        payload = build_enrich_contact_request(
            match_input=match_input,
            output_fields=output_fields,
        )
        return self._request(jwt, "POST", enrich_contact_url(self.base_url), json_body=payload)

    def enrich_company(
        self,
        jwt: str,
        *,
        match_input: list[dict[str, Any]],
        output_fields: list[str] | None = None,
    ) -> Any:
        """Enrich company data for one or more companies."""
        payload = build_enrich_company_request(
            match_input=match_input,
            output_fields=output_fields,
        )
        return self._request(jwt, "POST", enrich_company_url(self.base_url), json_body=payload)

    def enrich_ip(
        self,
        jwt: str,
        ip_address: str,
        *,
        output_fields: list[str] | None = None,
    ) -> Any:
        """Enrich data for a given IP address."""
        payload = build_enrich_ip_request(ip_address, output_fields=output_fields)
        return self._request(jwt, "POST", enrich_ip_url(self.base_url), json_body=payload)

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def bulk_enrich_contacts(
        self,
        jwt: str,
        *,
        match_input: list[dict[str, Any]],
        output_fields: list[str] | None = None,
    ) -> Any:
        """Submit a bulk contact enrichment job."""
        from harnessiq.providers.zoominfo.api import bulk_contact_url

        payload = build_bulk_contact_request(
            match_input=match_input,
            output_fields=output_fields,
        )
        return self._request(jwt, "POST", bulk_contact_url(self.base_url), json_body=payload)

    def bulk_enrich_companies(
        self,
        jwt: str,
        *,
        match_input: list[dict[str, Any]],
        output_fields: list[str] | None = None,
    ) -> Any:
        """Submit a bulk company enrichment job."""
        from harnessiq.providers.zoominfo.api import bulk_company_url

        payload = build_bulk_company_request(
            match_input=match_input,
            output_fields=output_fields,
        )
        return self._request(jwt, "POST", bulk_company_url(self.base_url), json_body=payload)

    # ------------------------------------------------------------------
    # Lookup & usage
    # ------------------------------------------------------------------

    def lookup_output_fields(self, jwt: str, entity: str) -> Any:
        """Retrieve the list of available output fields for a given entity type.

        Common entity values: ``"contact"``, ``"company"``.
        """
        return self._request(
            jwt,
            "GET",
            lookup_outputfields_url(self.base_url),
            json_body={"entity": entity},
        )

    def get_usage(self, jwt: str) -> Any:
        """Retrieve API usage and quota information."""
        return self._request(jwt, "GET", usage_url(self.base_url))

    def execute_operation(self, request: ProviderPayloadRequestDTO) -> ProviderPayloadResultDTO:
        """Execute one ZoomInfo operation from a DTO envelope."""

        get_zoominfo_operation(request.operation)
        return execute_payload_operation(self, request)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _request(
        self,
        jwt: str,
        method: str,
        url: str,
        *,
        json_body: Mapping[str, Any] | None = None,
    ) -> Any:
        return self.request_executor(
            method,
            url,
            headers=build_headers(jwt),
            json_body=dict(json_body) if json_body is not None else None,
            timeout_seconds=self.timeout_seconds,
        )
