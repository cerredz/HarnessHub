"""arXiv transport configuration and HTTP client."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any
from urllib import error, request

from harnessiq.providers.arxiv.api import (
    get_paper_url,
    parse_arxiv_feed,
    pdf_url,
    search_url,
)
from harnessiq.providers.http import ProviderHTTPError, RequestExecutor, request_json
from harnessiq.shared.dtos import ArxivOperationResultDTO, ProviderPayloadRequestDTO
from harnessiq.shared.provider_configs import ArxivConfig
from harnessiq.shared.provider_payloads import (
    optional_payload_int,
    optional_payload_string,
    require_payload_string,
)


@dataclass(frozen=True, slots=True)
class ArxivClient:
    """Minimal arXiv HTTP client for tool execution and tests.

    All search and retrieval operations use the public arXiv export API
    (no API key required). ``download_paper`` fetches PDF bytes via a
    separate binary HTTP request that bypasses ``request_executor``.

    Inject a custom ``request_executor`` in tests to avoid real network I/O.
    """

    config: ArxivConfig = field(default_factory=ArxivConfig)
    request_executor: RequestExecutor = request_json

    def search(
        self,
        *,
        query: str,
        max_results: int = 10,
        start: int = 0,
        sort_by: str = "relevance",
        sort_order: str = "descending",
    ) -> list[dict[str, Any]]:
        """Search arXiv papers and return normalized paper records.

        ``query`` supports arXiv field prefixes: ``ti:`` (title), ``au:``
        (author), ``abs:`` (abstract), ``cat:`` (category), ``all:`` (all
        fields). Boolean operators: ``AND``, ``OR``, ``ANDNOT``.
        """
        url = search_url(
            self.config.base_url,
            query=query,
            max_results=max_results,
            start=start,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        xml_text = self._fetch_xml(url)
        return parse_arxiv_feed(xml_text)

    def search_raw(
        self,
        *,
        query: str,
        max_results: int = 10,
        start: int = 0,
        sort_by: str = "relevance",
        sort_order: str = "descending",
    ) -> str:
        """Search arXiv papers and return the raw Atom 1.0 XML string."""
        url = search_url(
            self.config.base_url,
            query=query,
            max_results=max_results,
            start=start,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return self._fetch_xml(url)

    def get_paper(self, paper_id: str) -> dict[str, Any] | None:
        """Retrieve a single paper by arXiv ID.

        Returns a normalized paper record dict, or ``None`` if the paper is
        not found.
        """
        url = get_paper_url(self.config.base_url, paper_id)
        xml_text = self._fetch_xml(url)
        records = parse_arxiv_feed(xml_text)
        return records[0] if records else None

    def download_paper(self, paper_id: str, save_path: str) -> str:
        """Download the PDF for *paper_id* and write it to *save_path*.

        Returns *save_path* on success. Uses ``urllib.request`` directly
        because the PDF response is binary, not JSON or XML.
        """
        if self.config.delay_seconds > 0:
            time.sleep(self.config.delay_seconds)

        download_url = pdf_url(paper_id)
        try:
            with request.urlopen(
                download_url, timeout=self.config.timeout_seconds
            ) as resp:
                pdf_bytes: bytes = resp.read()
        except error.HTTPError as exc:
            raise ProviderHTTPError(
                provider="arxiv",
                message=exc.reason or "HTTP error",
                status_code=exc.code,
                url=download_url,
            ) from exc
        except error.URLError as exc:
            raise ProviderHTTPError(
                provider="arxiv",
                message=str(exc.reason),
                url=download_url,
            ) from exc

        with open(save_path, "wb") as fh:
            fh.write(pdf_bytes)
        return save_path

    def execute_operation(self, request: ProviderPayloadRequestDTO) -> ArxivOperationResultDTO:
        """Execute one arXiv operation from a DTO envelope."""
        payload = request.payload
        if request.operation == "search":
            results = self.search(
                query=require_payload_string(payload, "query"),
                max_results=optional_payload_int(payload, "max_results") or 10,
                start=optional_payload_int(payload, "start") or 0,
                sort_by=optional_payload_string(payload, "sort_by") or "relevance",
                sort_order=optional_payload_string(payload, "sort_order") or "descending",
            )
            return ArxivOperationResultDTO.from_search(results=results)
        if request.operation == "search_raw":
            xml = self.search_raw(
                query=require_payload_string(payload, "query"),
                max_results=optional_payload_int(payload, "max_results") or 10,
                start=optional_payload_int(payload, "start") or 0,
                sort_by=optional_payload_string(payload, "sort_by") or "relevance",
                sort_order=optional_payload_string(payload, "sort_order") or "descending",
            )
            return ArxivOperationResultDTO.from_search_raw(xml=xml)
        if request.operation == "get_paper":
            paper = self.get_paper(require_payload_string(payload, "paper_id"))
            return ArxivOperationResultDTO.from_get_paper(paper=paper)
        if request.operation == "download_paper":
            saved_to = self.download_paper(
                require_payload_string(payload, "paper_id"),
                require_payload_string(payload, "save_path"),
            )
            return ArxivOperationResultDTO.from_download_paper(saved_to=saved_to)
        raise ValueError(f"Unsupported arXiv operation '{request.operation}'.")

    def _fetch_xml(self, url: str) -> str:
        """Apply optional rate-limit delay then execute the request."""
        if self.config.delay_seconds > 0:
            time.sleep(self.config.delay_seconds)

        result = self.request_executor(
            "GET",
            url,
            headers={"Accept": "application/atom+xml"},
            timeout_seconds=self.config.timeout_seconds,
        )
        if not isinstance(result, str):
            raise ProviderHTTPError(
                provider="arxiv",
                message=(
                    f"Expected XML string response from arXiv, "
                    f"got {type(result).__name__}."
                ),
                url=url,
            )
        return result
