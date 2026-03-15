"""Creatify API endpoint constants and authentication helpers."""

from __future__ import annotations

from typing import Mapping

from harnessiq.providers.base import omit_none_values
from harnessiq.providers.http import join_url

DEFAULT_BASE_URL = "https://api.creatify.ai"


def build_headers(
    api_id: str,
    api_key: str,
    *,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build the headers required for Creatify API requests.

    Creatify authenticates via two custom headers: ``X-API-ID`` and
    ``X-API-KEY``, both obtained from the Creatify dashboard.
    """
    headers: dict[str, str] = {
        "X-API-ID": api_id,
        "X-API-KEY": api_key,
    }
    if extra_headers:
        headers.update(extra_headers)
    return headers


def url(base_url: str, path: str) -> str:
    """Return a fully qualified Creatify API URL."""
    return join_url(base_url, path)
