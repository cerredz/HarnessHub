"""Snov.io credential configuration type."""

from __future__ import annotations

from harnessiq.config.models import ProviderCredentialConfig


class SnovioCredentials(ProviderCredentialConfig, total=True):
    """Credentials for authenticating with the Snov.io API.

    Snov.io uses OAuth 2.0 client credentials.  Pass *client_id* and
    *client_secret* to ``SnovioClient`` to obtain an access token via
    :meth:`~harnessiq.providers.snovio.client.SnovioClient.get_access_token`.
    """

    client_id: str
    client_secret: str


__all__ = ["SnovioCredentials"]
