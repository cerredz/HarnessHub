"""Instantly API endpoint constants and authentication helpers."""

from __future__ import annotations

from typing import Mapping

from harnessiq.providers.http import join_url

DEFAULT_BASE_URL = "https://api.instantly.ai/api/v2"


def build_headers(
    api_key: str,
    *,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build the Authorization header for Instantly Bearer token auth."""
    headers: dict[str, str] = {"Authorization": f"Bearer {api_key}"}
    if extra_headers:
        headers.update(extra_headers)
    return headers


def url(base_url: str, path: str) -> str:
    """Return a fully qualified Instantly API URL."""
    return join_url(base_url, path)
