"""Proxycurl credential configuration type."""

from __future__ import annotations

from harnessiq.config.models import ProviderCredentialConfig


class ProxycurlCredentials(ProviderCredentialConfig, total=True):
    """Credentials for authenticating with the Proxycurl API.

    NOTE: Proxycurl shut down in January 2025 following a LinkedIn lawsuit.
    This provider is preserved for reference only.

    Pass the *api_key* as a Bearer token in the ``Authorization`` request header.
    """

    api_key: str


__all__ = ["ProxycurlCredentials"]
