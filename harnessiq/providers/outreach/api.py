"""Outreach API endpoint constants and authentication helpers."""

from __future__ import annotations

from typing import Mapping

from harnessiq.providers.http import join_url

DEFAULT_BASE_URL = "https://api.outreach.io/api/v2"


def build_headers(
    access_token: str,
    *,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build the Authorization header for Outreach OAuth Bearer token auth."""
    headers: dict[str, str] = {"Authorization": f"Bearer {access_token}"}
    if extra_headers:
        headers.update(extra_headers)
    return headers


def url(base_url: str, path: str) -> str:
    """Return a fully qualified Outreach API URL."""
    return join_url(base_url, path)
