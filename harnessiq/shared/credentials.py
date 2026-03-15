"""Shared credential TypedDicts for all data providers."""

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


class LeadIQCredentials(ProviderCredentialConfig, total=True):
    """Credentials for authenticating with the LeadIQ API.

    Pass the *api_key* in the ``X-Api-Key`` request header.
    """

    api_key: str


class SalesforgeCredentials(ProviderCredentialConfig, total=True):
    """Credentials for authenticating with the Salesforge API.

    Pass the *api_key* in the ``Authorization: Bearer {api_key}`` request header.
    """

    api_key: str


class PhantomBusterCredentials(ProviderCredentialConfig, total=True):
    """Credentials for authenticating with the PhantomBuster API.

    Pass the *api_key* in the ``X-Phantombuster-Key`` request header.
    """

    api_key: str


class ProxycurlCredentials(ProviderCredentialConfig, total=True):
    """Credentials for authenticating with the Proxycurl API.

    NOTE: Proxycurl shut down in January 2025 following a LinkedIn lawsuit.
    This provider is preserved for reference only.

    Pass the *api_key* as a Bearer token in the ``Authorization`` request header.
    """

    api_key: str


class ZoomInfoCredentials(ProviderCredentialConfig, total=True):
    """Credentials for authenticating with the ZoomInfo API.

    ZoomInfo uses a two-step auth: POST /authenticate with username+password
    to obtain a JWT, then pass the JWT as ``Authorization: Bearer {jwt}``.
    """

    username: str
    password: str


class PeopleDataLabsCredentials(ProviderCredentialConfig, total=True):
    """Credentials for authenticating with the People Data Labs API.

    Pass the *api_key* in the ``X-Api-Key`` request header.
    """

    api_key: str


class CoreSignalCredentials(ProviderCredentialConfig, total=True):
    """Credentials for authenticating with the Coresignal API.

    Pass the *api_key* in the ``apikey`` request header (lowercase, not
    ``Authorization`` or ``X-Api-Key``).
    """

    api_key: str


__all__ = [
    "CoreSignalCredentials",
    "LeadIQCredentials",
    "PeopleDataLabsCredentials",
    "PhantomBusterCredentials",
    "ProxycurlCredentials",
    "SalesforgeCredentials",
    "SnovioCredentials",
    "ZoomInfoCredentials",
]
