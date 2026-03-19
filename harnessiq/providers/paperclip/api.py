"""Paperclip API endpoint and authentication helpers."""

from __future__ import annotations

from typing import Mapping

from harnessiq.providers.http import join_url

DEFAULT_BASE_URL = "http://localhost:3100/api"


def build_headers(
    api_key: str,
    *,
    run_id: str | None = None,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build the headers required for Paperclip API requests."""
    headers: dict[str, str] = {
        "Authorization": f"Bearer {api_key}",
    }
    if run_id is not None:
        headers["X-Paperclip-Run-Id"] = run_id
    if extra_headers:
        headers.update(extra_headers)
    return headers


def url(base_url: str, path: str) -> str:
    """Return a fully qualified Paperclip API URL."""
    return join_url(base_url, path)


__all__ = [
    "DEFAULT_BASE_URL",
    "build_headers",
    "url",
]
