"""Anthropic endpoint and authentication helpers."""

from __future__ import annotations

from typing import Mapping, Sequence

from src.providers.base import omit_none_values
from src.providers.http import join_url

DEFAULT_BASE_URL = "https://api.anthropic.com"
DEFAULT_API_VERSION = "2023-06-01"


def build_headers(
    api_key: str,
    *,
    api_version: str = DEFAULT_API_VERSION,
    betas: Sequence[str] | None = None,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build the headers required for Anthropic API requests."""
    headers = omit_none_values(
        {
            "x-api-key": api_key,
            "anthropic-version": api_version,
            "anthropic-beta": ",".join(betas) if betas else None,
        }
    )
    if extra_headers:
        headers.update(extra_headers)
    return headers


def messages_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the Anthropic messages URL."""
    return join_url(base_url, "/v1/messages")


def count_tokens_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the Anthropic count-tokens URL."""
    return join_url(base_url, "/v1/messages/count_tokens")
