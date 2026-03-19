"""Lusha API endpoint constants and authentication helpers."""

from __future__ import annotations

from typing import Mapping

from harnessiq.providers.http import join_url

DEFAULT_BASE_URL = "https://api.lusha.com"


def build_headers(
    api_key: str,
    *,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build request headers for Lusha API key authentication.

    Lusha uses a lowercase ``api_key`` header (case-sensitive).
    """
    headers: dict[str, str] = {
        "api_key": api_key,
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)
    return headers


def url(base_url: str, path: str) -> str:
    """Return a fully qualified Lusha API URL."""
    return join_url(base_url, path)
