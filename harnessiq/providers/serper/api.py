"""Serper API endpoint constants and authentication helpers."""

from __future__ import annotations

from typing import Mapping

from harnessiq.providers.http import join_url

DEFAULT_BASE_URL = "https://google.serper.dev"


def build_headers(
    api_key: str,
    *,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build the API key header for Serper requests."""
    headers: dict[str, str] = {"X-API-KEY": api_key}
    if extra_headers:
        headers.update(extra_headers)
    return headers


def url(base_url: str, path: str) -> str:
    """Return a fully qualified Serper API URL."""
    return join_url(base_url, path)


__all__ = ["DEFAULT_BASE_URL", "build_headers", "url"]
