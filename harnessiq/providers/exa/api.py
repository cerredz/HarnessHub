"""Exa API endpoint constants and authentication helpers."""

from __future__ import annotations

from typing import Mapping

from harnessiq.providers.http import join_url

from harnessiq.shared.providers import EXA_DEFAULT_BASE_URL as DEFAULT_BASE_URL


def build_headers(
    api_key: str,
    *,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build the x-api-key header for Exa API key auth."""
    headers: dict[str, str] = {"x-api-key": api_key, "User-Agent": "Mozilla/5.0"}
    if extra_headers:
        headers.update(extra_headers)
    return headers


def url(base_url: str, path: str) -> str:
    """Return a fully qualified Exa API URL."""
    return join_url(base_url, path)

