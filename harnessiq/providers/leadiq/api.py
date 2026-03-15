"""LeadIQ endpoint and authentication helpers."""

from __future__ import annotations

from typing import Mapping

from harnessiq.providers.base import omit_none_values
from harnessiq.providers.http import join_url

DEFAULT_BASE_URL = "https://api.leadiq.com"


def build_headers(
    api_key: str,
    *,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build request headers for the LeadIQ API."""
    headers = omit_none_values({"X-Api-Key": api_key})
    if extra_headers:
        headers.update(extra_headers)
    return headers


def graphql_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the GraphQL endpoint URL."""
    return join_url(base_url, "/graphql")
