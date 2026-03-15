"""Arcads API endpoint constants and authentication helpers."""

from __future__ import annotations

import base64
from typing import Mapping

from harnessiq.providers.http import join_url

DEFAULT_BASE_URL = "https://external-api.arcads.ai"


def build_headers(
    client_id: str,
    client_secret: str,
    *,
    extra_headers: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build the Authorization header for Arcads Basic Auth.

    Arcads authenticates via HTTP Basic Auth with ``client_id`` as the
    username and ``client_secret`` as the password.  The credentials are
    Base64-encoded at request time so the raw secret is never stored in
    the header dict after this function returns.
    """
    token = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    headers: dict[str, str] = {"Authorization": f"Basic {token}"}
    if extra_headers:
        headers.update(extra_headers)
    return headers


def url(base_url: str, path: str) -> str:
    """Return a fully qualified Arcads API URL."""
    return join_url(base_url, path)
