"""LeadIQ endpoint and authentication helpers."""

from __future__ import annotations

import base64
from typing import Mapping

from harnessiq.providers.http import join_url

DEFAULT_BASE_URL = "https://api.leadiq.com"


def build_headers(
    api_key: str,
    *,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build request headers for the LeadIQ API.

    LeadIQ uses HTTP Basic authentication where the API key is the username
    and the password is empty.  The encoded value is ``base64("api_key:")``.
    """
    encoded = base64.b64encode(f"{api_key}:".encode("utf-8")).decode("ascii")
    headers: dict[str, str] = {"Authorization": f"Basic {encoded}"}
    if extra_headers:
        headers.update(extra_headers)
    return headers


def graphql_url(base_url: str = DEFAULT_BASE_URL) -> str:
    """Return the GraphQL endpoint URL."""
    return join_url(base_url, "/graphql")
