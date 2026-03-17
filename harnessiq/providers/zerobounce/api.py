"""ZeroBounce API endpoint constants and authentication helpers."""

from __future__ import annotations

from typing import Mapping

from harnessiq.providers.http import join_url

DEFAULT_BASE_URL = "https://api.zerobounce.net"
DEFAULT_BULK_BASE_URL = "https://bulkapi.zerobounce.net"


def build_headers(
    *,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build base request headers for ZeroBounce.

    ZeroBounce authenticates via ``api_key`` as a query parameter, not a
    header.  This function returns only the Content-Type header; the api_key
    is injected into the URL by ``_build_prepared_request``.
    """
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    return headers


def url(base_url: str, path: str) -> str:
    """Return a fully qualified ZeroBounce API URL."""
    return join_url(base_url, path)
