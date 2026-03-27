"""Hunter.io API endpoint constants and authentication helpers."""

from __future__ import annotations

from typing import Mapping

from harnessiq.providers.http import join_url
from harnessiq.shared.providers import HUNTER_DEFAULT_BASE_URL as DEFAULT_BASE_URL


def build_headers(
    *,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build base request headers for Hunter.

    Hunter authentication is injected via the ``api_key`` query parameter, not
    request headers.
    """

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    return headers


def url(
    base_url: str,
    path: str,
    *,
    query: Mapping[str, str | int | float | bool] | None = None,
) -> str:
    """Return a fully qualified Hunter API URL."""

    return join_url(base_url, path, query=query)


__all__ = [
    "DEFAULT_BASE_URL",
    "build_headers",
    "url",
]
