"""Expandi API endpoint constants and authentication helpers."""

from __future__ import annotations

from typing import Mapping

from harnessiq.providers.http import join_url

from harnessiq.shared.providers import EXPANDI_DEFAULT_BASE_URL as DEFAULT_BASE_URL


def build_headers(
    *,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build base request headers for Expandi.

    Expandi authenticates via ``key`` and ``secret`` as query parameters,
    not as headers.  This function returns only Content-Type; auth params
    are injected into the URL by ``_build_prepared_request``.
    """
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    return headers


def url(base_url: str, path: str) -> str:
    """Return a fully qualified Expandi API URL."""
    return join_url(base_url, path)

