"""Provider-family credential specs used by the platform CLI."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Mapping

from harnessiq.shared.credentials import (
    ApolloCredentials,
    ArcadsCredentials,
    AttioCredentials,
    BrowserUseCredentials,
    CoreSignalCredentials,
    CreatifyCredentials,
    ExaCredentials,
    ExpandiCredentials,
    InboxAppCredentials,
    InstantlyCredentials,
    LeadIQCredentials,
    LemlistCredentials,
    LushaCredentials,
    OutreachCredentials,
    PaperclipCredentials,
    PeopleDataLabsCredentials,
    PhantomBusterCredentials,
    ProxycurlCredentials,
    SalesforgeCredentials,
    SerperCredentials,
    SmartleadCredentials,
    SnovioCredentials,
    ZeroBounceCredentials,
    ZoomInfoCredentials,
)
from harnessiq.shared.google_drive import GoogleDriveCredentials
from harnessiq.shared.resend import ResendCredentials


@dataclass(frozen=True, slots=True)
class ProviderCredentialFieldSpec:
    """One bindable credential field for a provider family."""

    name: str
    description: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Provider credential field name must not be blank.")
        if not self.description.strip():
            raise ValueError("Provider credential field description must not be blank.")


@dataclass(frozen=True, slots=True)
class ProviderCredentialSpec:
    """Constructor metadata for one provider family's credential object."""

    family: str
    description: str
    fields: tuple[ProviderCredentialFieldSpec, ...]
    builder: Callable[[Mapping[str, str]], object]

    def __post_init__(self) -> None:
        normalized_family = self.family.strip().lower()
        if not normalized_family:
            raise ValueError("Provider credential family must not be blank.")
        if not self.description.strip():
            raise ValueError("Provider credential description must not be blank.")
        if not self.fields:
            raise ValueError("Provider credential specs must declare at least one field.")
        object.__setattr__(self, "family", normalized_family)
        object.__setattr__(self, "fields", tuple(self.fields))

    @property
    def field_names(self) -> tuple[str, ...]:
        return tuple(field.name for field in self.fields)

    def validate_fields(self, values: Mapping[str, str]) -> dict[str, str]:
        normalized = {str(key): str(value) for key, value in values.items()}
        missing = [field.name for field in self.fields if not normalized.get(field.name, "").strip()]
        if missing:
            rendered = ", ".join(missing)
            raise ValueError(f"Provider family '{self.family}' is missing required credential fields: {rendered}.")
        unsupported = sorted(set(normalized) - set(self.field_names))
        if unsupported:
            rendered = ", ".join(unsupported)
            raise ValueError(f"Provider family '{self.family}' does not support credential fields: {rendered}.")
        return {key: normalized[key] for key in self.field_names}

    def build_credentials(self, values: Mapping[str, str]) -> object:
        return self.builder(self.validate_fields(values))

    def redact_values(self, values: Mapping[str, str]) -> dict[str, str]:
        return {key: _mask_secret(value) for key, value in self.validate_fields(values).items()}


def _mask_secret(value: str) -> str:
    stripped = value.strip()
    if len(stripped) <= 4:
        return "*" * len(stripped)
    return f"{stripped[:2]}{'*' * max(1, len(stripped) - 4)}{stripped[-2:]}"


def _dataclass_builder(cls):
    def build(values: Mapping[str, str]) -> object:
        return cls(**dict(values))

    return build


PROVIDER_CREDENTIAL_SPECS = MappingProxyType(
    {
        "apollo": ProviderCredentialSpec(
            family="apollo",
            description="Apollo REST API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "Apollo API key."),),
            builder=_dataclass_builder(ApolloCredentials),
        ),
        "arcads": ProviderCredentialSpec(
            family="arcads",
            description="Arcads API credentials.",
            fields=(
                ProviderCredentialFieldSpec("client_id", "Arcads client id."),
                ProviderCredentialFieldSpec("client_secret", "Arcads client secret."),
            ),
            builder=_dataclass_builder(ArcadsCredentials),
        ),
        "attio": ProviderCredentialSpec(
            family="attio",
            description="Attio API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "Attio API key."),),
            builder=_dataclass_builder(AttioCredentials),
        ),
        "browser_use": ProviderCredentialSpec(
            family="browser_use",
            description="Browser Use Cloud API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "Browser Use API key."),),
            builder=_dataclass_builder(BrowserUseCredentials),
        ),
        "coresignal": ProviderCredentialSpec(
            family="coresignal",
            description="Coresignal API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "Coresignal API key."),),
            builder=lambda values: CoreSignalCredentials(**dict(values)),
        ),
        "creatify": ProviderCredentialSpec(
            family="creatify",
            description="Creatify API credentials.",
            fields=(
                ProviderCredentialFieldSpec("api_id", "Creatify API id."),
                ProviderCredentialFieldSpec("api_key", "Creatify API key."),
            ),
            builder=_dataclass_builder(CreatifyCredentials),
        ),
        "exa": ProviderCredentialSpec(
            family="exa",
            description="Exa API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "Exa API key."),),
            builder=_dataclass_builder(ExaCredentials),
        ),
        "expandi": ProviderCredentialSpec(
            family="expandi",
            description="Expandi API credentials.",
            fields=(
                ProviderCredentialFieldSpec("api_key", "Expandi API key."),
                ProviderCredentialFieldSpec("api_secret", "Expandi API secret."),
            ),
            builder=_dataclass_builder(ExpandiCredentials),
        ),
        "google_drive": ProviderCredentialSpec(
            family="google_drive",
            description="Google Drive OAuth credentials.",
            fields=(
                ProviderCredentialFieldSpec("client_id", "Google OAuth client id."),
                ProviderCredentialFieldSpec("client_secret", "Google OAuth client secret."),
                ProviderCredentialFieldSpec("refresh_token", "Google OAuth refresh token."),
            ),
            builder=_dataclass_builder(GoogleDriveCredentials),
        ),
        "inboxapp": ProviderCredentialSpec(
            family="inboxapp",
            description="InboxApp API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "InboxApp API key."),),
            builder=_dataclass_builder(InboxAppCredentials),
        ),
        "instantly": ProviderCredentialSpec(
            family="instantly",
            description="Instantly API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "Instantly API key."),),
            builder=_dataclass_builder(InstantlyCredentials),
        ),
        "leadiq": ProviderCredentialSpec(
            family="leadiq",
            description="LeadIQ API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "LeadIQ API key."),),
            builder=lambda values: LeadIQCredentials(**dict(values)),
        ),
        "lemlist": ProviderCredentialSpec(
            family="lemlist",
            description="Lemlist API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "Lemlist API key."),),
            builder=_dataclass_builder(LemlistCredentials),
        ),
        "lusha": ProviderCredentialSpec(
            family="lusha",
            description="Lusha API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "Lusha API key."),),
            builder=_dataclass_builder(LushaCredentials),
        ),
        "outreach": ProviderCredentialSpec(
            family="outreach",
            description="Outreach API credentials.",
            fields=(ProviderCredentialFieldSpec("access_token", "Outreach access token."),),
            builder=_dataclass_builder(OutreachCredentials),
        ),
        "paperclip": ProviderCredentialSpec(
            family="paperclip",
            description="Paperclip API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "Paperclip API key."),),
            builder=_dataclass_builder(PaperclipCredentials),
        ),
        "peopledatalabs": ProviderCredentialSpec(
            family="peopledatalabs",
            description="People Data Labs API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "People Data Labs API key."),),
            builder=lambda values: PeopleDataLabsCredentials(**dict(values)),
        ),
        "phantombuster": ProviderCredentialSpec(
            family="phantombuster",
            description="PhantomBuster API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "PhantomBuster API key."),),
            builder=lambda values: PhantomBusterCredentials(**dict(values)),
        ),
        "proxycurl": ProviderCredentialSpec(
            family="proxycurl",
            description="Proxycurl API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "Proxycurl API key."),),
            builder=lambda values: ProxycurlCredentials(**dict(values)),
        ),
        "resend": ProviderCredentialSpec(
            family="resend",
            description="Resend API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "Resend API key."),),
            builder=_dataclass_builder(ResendCredentials),
        ),
        "salesforge": ProviderCredentialSpec(
            family="salesforge",
            description="Salesforge API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "Salesforge API key."),),
            builder=lambda values: SalesforgeCredentials(**dict(values)),
        ),
        "serper": ProviderCredentialSpec(
            family="serper",
            description="Serper API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "Serper API key."),),
            builder=_dataclass_builder(SerperCredentials),
        ),
        "smartlead": ProviderCredentialSpec(
            family="smartlead",
            description="Smartlead API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "Smartlead API key."),),
            builder=lambda values: SmartleadCredentials(**dict(values)),
        ),
        "snovio": ProviderCredentialSpec(
            family="snovio",
            description="Snov.io API credentials.",
            fields=(
                ProviderCredentialFieldSpec("client_id", "Snov.io client id."),
                ProviderCredentialFieldSpec("client_secret", "Snov.io client secret."),
            ),
            builder=lambda values: SnovioCredentials(**dict(values)),
        ),
        "zerobounce": ProviderCredentialSpec(
            family="zerobounce",
            description="ZeroBounce API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "ZeroBounce API key."),),
            builder=lambda values: ZeroBounceCredentials(**dict(values)),
        ),
        "zoominfo": ProviderCredentialSpec(
            family="zoominfo",
            description="ZoomInfo API credentials.",
            fields=(
                ProviderCredentialFieldSpec("username", "ZoomInfo username."),
                ProviderCredentialFieldSpec("password", "ZoomInfo password."),
            ),
            builder=lambda values: ZoomInfoCredentials(**dict(values)),
        ),
    }
)


def get_provider_credential_spec(family: str) -> ProviderCredentialSpec:
    normalized_family = family.strip().lower()
    if normalized_family not in PROVIDER_CREDENTIAL_SPECS:
        raise KeyError(f"No provider credential spec exists for '{family}'.")
    return PROVIDER_CREDENTIAL_SPECS[normalized_family]


def list_provider_credential_specs() -> tuple[ProviderCredentialSpec, ...]:
    return tuple(PROVIDER_CREDENTIAL_SPECS.values())


__all__ = [
    "PROVIDER_CREDENTIAL_SPECS",
    "ProviderCredentialFieldSpec",
    "ProviderCredentialSpec",
    "get_provider_credential_spec",
    "list_provider_credential_specs",
]
