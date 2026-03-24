"""Shared provider credential and transport-auth definitions."""

from __future__ import annotations

from dataclasses import dataclass

from harnessiq.config.models import ProviderCredentialConfig
from harnessiq.shared.providers import (
    APOLLO_DEFAULT_BASE_URL,
    ARCADS_DEFAULT_BASE_URL,
    ATTIO_DEFAULT_BASE_URL,
    BROWSER_USE_DEFAULT_BASE_URL,
    CREATIFY_DEFAULT_BASE_URL,
    EXA_DEFAULT_BASE_URL,
    EXPANDI_DEFAULT_BASE_URL,
    INBOXAPP_DEFAULT_BASE_URL,
    INSTANTLY_DEFAULT_BASE_URL,
    LEMLIST_DEFAULT_BASE_URL,
    LUSHA_DEFAULT_BASE_URL,
    OUTREACH_DEFAULT_BASE_URL,
    PAPERCLIP_DEFAULT_BASE_URL,
    SERPER_DEFAULT_BASE_URL,
    SMARTLEAD_DEFAULT_BASE_URL,
    ZEROBOUNCE_DEFAULT_BASE_URL,
    ZEROBOUNCE_DEFAULT_BULK_BASE_URL,
)


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


@dataclass(frozen=True, slots=True)
class ApolloCredentials:
    """Runtime credentials for the Apollo REST API."""

    api_key: str
    base_url: str = APOLLO_DEFAULT_BASE_URL
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("Apollo api_key must not be blank.")
        if not self.base_url.strip():
            raise ValueError("Apollo base_url must not be blank.")
        if self.timeout_seconds <= 0:
            raise ValueError("Apollo timeout_seconds must be greater than zero.")

    def masked_api_key(self) -> str:
        api_key = self.api_key
        if len(api_key) <= 4:
            return "*" * len(api_key)
        return f"{api_key[:3]}{'*' * max(1, len(api_key) - 7)}{api_key[-4:]}"

    def as_redacted_dict(self) -> dict[str, object]:
        return {
            "api_key_masked": self.masked_api_key(),
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class ArcadsCredentials:
    """Runtime credentials for the Arcads AI video ad API."""

    client_id: str
    client_secret: str
    base_url: str = ARCADS_DEFAULT_BASE_URL
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.client_id.strip():
            raise ValueError("Arcads client_id must not be blank.")
        if not self.client_secret.strip():
            raise ValueError("Arcads client_secret must not be blank.")
        if not self.base_url.strip():
            raise ValueError("Arcads base_url must not be blank.")
        if self.timeout_seconds <= 0:
            raise ValueError("Arcads timeout_seconds must be greater than zero.")

    def masked_client_secret(self) -> str:
        secret = self.client_secret
        if len(secret) <= 4:
            return "*" * len(secret)
        return f"{secret[:3]}{'*' * max(1, len(secret) - 7)}{secret[-4:]}"

    def as_redacted_dict(self) -> dict[str, object]:
        return {
            "client_id": self.client_id,
            "client_secret_masked": self.masked_client_secret(),
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class AttioCredentials:
    """Runtime credentials for the Attio REST API."""

    api_key: str
    base_url: str = ATTIO_DEFAULT_BASE_URL
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("Attio api_key must not be blank.")
        if not self.base_url.strip():
            raise ValueError("Attio base_url must not be blank.")
        if self.timeout_seconds <= 0:
            raise ValueError("Attio timeout_seconds must be greater than zero.")

    def masked_api_key(self) -> str:
        key = self.api_key
        if len(key) <= 4:
            return "*" * len(key)
        return f"{key[:3]}{'*' * max(1, len(key) - 7)}{key[-4:]}"

    def as_redacted_dict(self) -> dict[str, object]:
        return {
            "api_key_masked": self.masked_api_key(),
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class BrowserUseCredentials:
    """Runtime credentials for the Browser Use Cloud API."""

    api_key: str
    base_url: str = BROWSER_USE_DEFAULT_BASE_URL
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("Browser Use api_key must not be blank.")
        if not self.base_url.strip():
            raise ValueError("Browser Use base_url must not be blank.")
        if self.timeout_seconds <= 0:
            raise ValueError("Browser Use timeout_seconds must be greater than zero.")

    def masked_api_key(self) -> str:
        key = self.api_key
        if len(key) <= 4:
            return "*" * len(key)
        return f"{key[:3]}{'*' * max(1, len(key) - 7)}{key[-4:]}"

    def as_redacted_dict(self) -> dict[str, object]:
        return {
            "api_key_masked": self.masked_api_key(),
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class CreatifyCredentials:
    """Runtime credentials for the Creatify API."""

    api_id: str
    api_key: str
    base_url: str = CREATIFY_DEFAULT_BASE_URL
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.api_id.strip():
            raise ValueError("Creatify api_id must not be blank.")
        if not self.api_key.strip():
            raise ValueError("Creatify api_key must not be blank.")
        if not self.base_url.strip():
            raise ValueError("Creatify base_url must not be blank.")
        if self.timeout_seconds <= 0:
            raise ValueError("Creatify timeout_seconds must be greater than zero.")

    def masked_api_key(self) -> str:
        key = self.api_key
        if len(key) <= 4:
            return "*" * len(key)
        return f"{key[:3]}{'*' * max(1, len(key) - 7)}{key[-4:]}"

    def as_redacted_dict(self) -> dict[str, object]:
        return {
            "api_id": self.api_id,
            "api_key_masked": self.masked_api_key(),
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class ExaCredentials:
    """Runtime credentials for the Exa API."""

    api_key: str
    base_url: str = EXA_DEFAULT_BASE_URL
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("Exa api_key must not be blank.")
        if not self.base_url.strip():
            raise ValueError("Exa base_url must not be blank.")
        if self.timeout_seconds <= 0:
            raise ValueError("Exa timeout_seconds must be greater than zero.")

    def masked_api_key(self) -> str:
        key = self.api_key
        if len(key) <= 4:
            return "*" * len(key)
        return f"{key[:3]}{'*' * max(1, len(key) - 7)}{key[-4:]}"

    def as_redacted_dict(self) -> dict[str, object]:
        return {
            "api_key_masked": self.masked_api_key(),
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class ExpandiCredentials:
    """Runtime credentials for the Expandi LinkedIn automation API."""

    api_key: str
    api_secret: str
    base_url: str = EXPANDI_DEFAULT_BASE_URL
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("Expandi api_key must not be blank.")
        if not self.api_secret.strip():
            raise ValueError("Expandi api_secret must not be blank.")
        if not self.base_url.strip():
            raise ValueError("Expandi base_url must not be blank.")
        if self.timeout_seconds <= 0:
            raise ValueError("Expandi timeout_seconds must be greater than zero.")

    def masked_api_key(self) -> str:
        key = self.api_key
        if len(key) <= 4:
            return "*" * len(key)
        return f"{key[:3]}{'*' * max(1, len(key) - 7)}{key[-4:]}"

    def masked_api_secret(self) -> str:
        secret = self.api_secret
        if len(secret) <= 4:
            return "*" * len(secret)
        return f"{secret[:3]}{'*' * max(1, len(secret) - 7)}{secret[-4:]}"

    def as_redacted_dict(self) -> dict[str, object]:
        return {
            "api_key_masked": self.masked_api_key(),
            "api_secret_masked": self.masked_api_secret(),
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class InboxAppCredentials:
    """Runtime credentials for the InboxApp API."""

    api_key: str
    base_url: str = INBOXAPP_DEFAULT_BASE_URL
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("InboxApp api_key must not be blank.")
        if not self.base_url.strip():
            raise ValueError("InboxApp base_url must not be blank.")
        if self.timeout_seconds <= 0:
            raise ValueError("InboxApp timeout_seconds must be greater than zero.")

    def masked_api_key(self) -> str:
        key = self.api_key
        if len(key) <= 4:
            return "*" * len(key)
        return f"{key[:3]}{'*' * max(1, len(key) - 7)}{key[-4:]}"

    def as_redacted_dict(self) -> dict[str, object]:
        return {
            "api_key_masked": self.masked_api_key(),
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class InstantlyCredentials:
    """Runtime credentials for the Instantly API."""

    api_key: str
    base_url: str = INSTANTLY_DEFAULT_BASE_URL
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("Instantly api_key must not be blank.")
        if not self.base_url.strip():
            raise ValueError("Instantly base_url must not be blank.")
        if self.timeout_seconds <= 0:
            raise ValueError("Instantly timeout_seconds must be greater than zero.")

    def masked_api_key(self) -> str:
        key = self.api_key
        if len(key) <= 4:
            return "*" * len(key)
        return f"{key[:3]}{'*' * max(1, len(key) - 7)}{key[-4:]}"

    def as_redacted_dict(self) -> dict[str, object]:
        return {
            "api_key_masked": self.masked_api_key(),
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class LemlistCredentials:
    """Runtime credentials for the Lemlist API."""

    api_key: str
    base_url: str = LEMLIST_DEFAULT_BASE_URL
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("Lemlist api_key must not be blank.")
        if not self.base_url.strip():
            raise ValueError("Lemlist base_url must not be blank.")
        if self.timeout_seconds <= 0:
            raise ValueError("Lemlist timeout_seconds must be greater than zero.")

    def masked_api_key(self) -> str:
        key = self.api_key
        if len(key) <= 4:
            return "*" * len(key)
        return f"{key[:3]}{'*' * max(1, len(key) - 7)}{key[-4:]}"

    def as_redacted_dict(self) -> dict[str, object]:
        return {
            "api_key_masked": self.masked_api_key(),
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class LushaCredentials:
    """Runtime credentials for the Lusha API."""

    api_key: str
    base_url: str = LUSHA_DEFAULT_BASE_URL
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("Lusha api_key must not be blank.")
        if not self.base_url.strip():
            raise ValueError("Lusha base_url must not be blank.")
        if self.timeout_seconds <= 0:
            raise ValueError("Lusha timeout_seconds must be greater than zero.")

    def masked_api_key(self) -> str:
        key = self.api_key
        if len(key) <= 4:
            return "*" * len(key)
        return f"{key[:3]}{'*' * max(1, len(key) - 7)}{key[-4:]}"

    def as_redacted_dict(self) -> dict[str, object]:
        return {
            "api_key_masked": self.masked_api_key(),
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class OutreachCredentials:
    """Runtime credentials for the Outreach API."""

    access_token: str
    base_url: str = OUTREACH_DEFAULT_BASE_URL
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.access_token.strip():
            raise ValueError("Outreach access_token must not be blank.")
        if not self.base_url.strip():
            raise ValueError("Outreach base_url must not be blank.")
        if self.timeout_seconds <= 0:
            raise ValueError("Outreach timeout_seconds must be greater than zero.")

    def masked_access_token(self) -> str:
        token = self.access_token
        if len(token) <= 4:
            return "*" * len(token)
        return f"{token[:3]}{'*' * max(1, len(token) - 7)}{token[-4:]}"

    def as_redacted_dict(self) -> dict[str, object]:
        return {
            "access_token_masked": self.masked_access_token(),
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class PaperclipCredentials:
    """Runtime credentials for the Paperclip control-plane API."""

    api_key: str
    base_url: str = PAPERCLIP_DEFAULT_BASE_URL
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("Paperclip api_key must not be blank.")
        if not self.base_url.strip():
            raise ValueError("Paperclip base_url must not be blank.")
        if self.timeout_seconds <= 0:
            raise ValueError("Paperclip timeout_seconds must be greater than zero.")

    def masked_api_key(self) -> str:
        key = self.api_key
        if len(key) <= 4:
            return "*" * len(key)
        return f"{key[:3]}{'*' * max(1, len(key) - 7)}{key[-4:]}"

    def as_redacted_dict(self) -> dict[str, object]:
        return {
            "api_key_masked": self.masked_api_key(),
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class SerperCredentials:
    """Runtime credentials for the Serper API."""

    api_key: str
    base_url: str = SERPER_DEFAULT_BASE_URL
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("Serper api_key must not be blank.")
        if not self.base_url.strip():
            raise ValueError("Serper base_url must not be blank.")
        if self.timeout_seconds <= 0:
            raise ValueError("Serper timeout_seconds must be greater than zero.")

    def masked_api_key(self) -> str:
        key = self.api_key
        if len(key) <= 4:
            return "*" * len(key)
        return f"{key[:3]}{'*' * max(1, len(key) - 7)}{key[-4:]}"

    def as_redacted_dict(self) -> dict[str, object]:
        return {
            "api_key_masked": self.masked_api_key(),
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class SmartleadCredentials:
    """Runtime credentials for the Smartlead API."""

    api_key: str
    base_url: str = SMARTLEAD_DEFAULT_BASE_URL
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("Smartlead api_key must not be blank.")
        if not self.base_url.strip():
            raise ValueError("Smartlead base_url must not be blank.")
        if self.timeout_seconds <= 0:
            raise ValueError("Smartlead timeout_seconds must be greater than zero.")

    def masked_api_key(self) -> str:
        key = self.api_key
        if len(key) <= 4:
            return "*" * len(key)
        return f"{key[:3]}{'*' * max(1, len(key) - 7)}{key[-4:]}"

    def as_redacted_dict(self) -> dict[str, object]:
        return {
            "api_key_masked": self.masked_api_key(),
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True, slots=True)
class ZeroBounceCredentials:
    """Runtime credentials for the ZeroBounce email validation API."""

    api_key: str
    base_url: str = ZEROBOUNCE_DEFAULT_BASE_URL
    bulk_base_url: str = ZEROBOUNCE_DEFAULT_BULK_BASE_URL
    timeout_seconds: float = 60.0

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("ZeroBounce api_key must not be blank.")
        if not self.base_url.strip():
            raise ValueError("ZeroBounce base_url must not be blank.")
        if not self.bulk_base_url.strip():
            raise ValueError("ZeroBounce bulk_base_url must not be blank.")
        if self.timeout_seconds <= 0:
            raise ValueError("ZeroBounce timeout_seconds must be greater than zero.")

    def masked_api_key(self) -> str:
        key = self.api_key
        if len(key) <= 4:
            return "*" * len(key)
        return f"{key[:3]}{'*' * max(1, len(key) - 7)}{key[-4:]}"

    def as_redacted_dict(self) -> dict[str, object]:
        return {
            "api_key_masked": self.masked_api_key(),
            "base_url": self.base_url,
            "bulk_base_url": self.bulk_base_url,
            "timeout_seconds": self.timeout_seconds,
        }


__all__ = [
    "ApolloCredentials",
    "ArcadsCredentials",
    "AttioCredentials",
    "BrowserUseCredentials",
    "CoreSignalCredentials",
    "CreatifyCredentials",
    "ExaCredentials",
    "ExpandiCredentials",
    "InboxAppCredentials",
    "InstantlyCredentials",
    "LeadIQCredentials",
    "LemlistCredentials",
    "LushaCredentials",
    "OutreachCredentials",
    "PaperclipCredentials",
    "PeopleDataLabsCredentials",
    "PhantomBusterCredentials",
    "ProxycurlCredentials",
    "SerperCredentials",
    "SalesforgeCredentials",
    "SmartleadCredentials",
    "SnovioCredentials",
    "ZeroBounceCredentials",
    "ZoomInfoCredentials",
]
