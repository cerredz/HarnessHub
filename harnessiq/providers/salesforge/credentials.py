"""Salesforge credential configuration type."""

from __future__ import annotations

from harnessiq.config.models import ProviderCredentialConfig


class SalesforgeCredentials(ProviderCredentialConfig, total=True):
    """Credentials for authenticating with the Salesforge API.

    Pass the *api_key* in the ``Authorization: Bearer {api_key}`` request header.
    """

    api_key: str


__all__ = ["SalesforgeCredentials"]
