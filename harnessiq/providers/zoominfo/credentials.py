"""ZoomInfo credential configuration type."""

from __future__ import annotations

from harnessiq.config.models import ProviderCredentialConfig


class ZoomInfoCredentials(ProviderCredentialConfig, total=True):
    """Credentials for authenticating with the ZoomInfo API.

    ZoomInfo uses a two-step auth: POST /authenticate with username+password
    to obtain a JWT, then pass the JWT as ``Authorization: Bearer {jwt}``.
    """

    username: str
    password: str


__all__ = ["ZoomInfoCredentials"]
