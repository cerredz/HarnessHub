"""LeadIQ credential configuration type."""

from __future__ import annotations

from harnessiq.config.models import ProviderCredentialConfig


class LeadIQCredentials(ProviderCredentialConfig, total=True):
    """Credentials for authenticating with the LeadIQ API.

    Pass the *api_key* in the ``X-Api-Key`` request header.
    """

    api_key: str


__all__ = ["LeadIQCredentials"]
