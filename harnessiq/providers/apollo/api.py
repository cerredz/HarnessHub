"""Apollo API endpoint constants and authentication helpers."""

from __future__ import annotations

from typing import Mapping

from harnessiq.providers.http import join_url

from harnessiq.shared.providers import APOLLO_DEFAULT_BASE_URL as DEFAULT_BASE_URL


def build_headers(
    api_key: str,
    *,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build Apollo authentication headers.

    Apollo's tutorial documentation uses ``X-Api-Key``. The reference UI also
    presents API-key auth as a bearer-style credential, so both headers are
    included for compatibility.
    """
    headers: dict[str, str] = {
        "Authorization": f"Bearer {api_key}",
        "Cache-Control": "no-cache",
        "X-Api-Key": api_key,
    }
    if extra_headers:
        headers.update(extra_headers)
    return headers


def url(
    base_url: str,
    path: str,
    *,
    query: Mapping[str, str | int | float | bool] | None = None,
) -> str:
    """Return a fully qualified Apollo API URL."""
    return join_url(base_url, path, query=query)


__all__ = [
    "DEFAULT_BASE_URL",
    "build_headers",
    "url",
]

