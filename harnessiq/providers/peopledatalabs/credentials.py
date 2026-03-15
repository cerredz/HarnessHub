"""People Data Labs credential configuration type."""

from __future__ import annotations

from harnessiq.config.models import ProviderCredentialConfig


class PeopleDataLabsCredentials(ProviderCredentialConfig, total=True):
    """Credentials for authenticating with the People Data Labs API.

    Pass the *api_key* in the ``X-Api-Key`` request header.
    """

    api_key: str


__all__ = ["PeopleDataLabsCredentials"]
