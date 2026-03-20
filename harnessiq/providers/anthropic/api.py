"""Anthropic endpoint and authentication helpers."""

from __future__ import annotations

from typing import Mapping, Sequence

from harnessiq.providers.base import omit_none_values
from harnessiq.providers.http import join_url
from harnessiq.shared.providers import (
    ANTHROPIC_DEFAULT_API_VERSION as DEFAULT_API_VERSION,
    ANTHROPIC_DEFAULT_BASE_URL as DEFAULT_BASE_URL,
)


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
