"""Coresignal credential configuration type."""

from __future__ import annotations

from harnessiq.config.models import ProviderCredentialConfig


class CoreSignalCredentials(ProviderCredentialConfig, total=True):
    """Credentials for authenticating with the Coresignal API.

    Pass the *api_key* in the ``apikey`` request header (lowercase, not
    ``Authorization`` or ``X-Api-Key``).
    """

    api_key: str


__all__ = ["CoreSignalCredentials"]
