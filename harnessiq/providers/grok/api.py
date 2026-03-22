"""xAI/Grok endpoint and authentication helpers."""

from __future__ import annotations

from typing import Mapping

from harnessiq.providers.base import omit_none_values
from harnessiq.providers.http import join_url

from harnessiq.shared.providers import GROK_DEFAULT_BASE_URL as DEFAULT_BASE_URL


def build_headers(
    api_key: str,
    *,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build the headers required for xAI API requests."""
    headers = omit_none_values(
        {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Mozilla/5.0",
        }
    )
    if extra_headers:
        headers.update(extra_headers)
    return headers


def chat_completions_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the xAI chat completions URL."""
    return join_url(base_url, "/v1/chat/completions")


def models_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the xAI models URL."""
    return join_url(base_url, "/v1/models")

