"""PhantomBuster credential configuration type."""

from __future__ import annotations

from harnessiq.config.models import ProviderCredentialConfig


class PhantomBusterCredentials(ProviderCredentialConfig, total=True):
    """Credentials for authenticating with the PhantomBuster API.

    Pass the *api_key* in the ``X-Phantombuster-Key`` request header.
    """

    api_key: str


__all__ = ["PhantomBusterCredentials"]
