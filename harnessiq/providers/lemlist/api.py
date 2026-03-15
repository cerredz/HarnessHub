"""Lemlist API endpoint constants and authentication helpers."""

from __future__ import annotations

import base64
from typing import Mapping

from harnessiq.providers.http import join_url

DEFAULT_BASE_URL = "https://api.lemlist.com/api"


def build_headers(
    api_key: str,
    *,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build the Authorization header for Lemlist Basic Auth.

    Lemlist authenticates via HTTP Basic Auth with an empty username and the
    API key as the password.
    """
    token = base64.b64encode(f":{api_key}".encode()).decode()
    headers: dict[str, str] = {"Authorization": f"Basic {token}"}
    if extra_headers:
        headers.update(extra_headers)
    return headers


def url(base_url: str, path: str) -> str:
    """Return a fully qualified Lemlist API URL."""
    return join_url(base_url, path)
