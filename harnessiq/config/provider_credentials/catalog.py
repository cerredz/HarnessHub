"""Static provider credential catalog definitions."""

from __future__ import annotations

from types import MappingProxyType

from harnessiq.shared.credentials import (
    ApolloCredentials,
    ArcadsCredentials,
    AttioCredentials,
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

from .builders import build_dataclass_credential_builder
from .models import ProviderCredentialFieldSpec, ProviderCredentialSpec


PROVIDER_CREDENTIAL_SPECS = MappingProxyType(
    {
        "apollo": ProviderCredentialSpec(
            family="apollo",
            description="Apollo REST API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "Apollo API key."),),
            builder=build_dataclass_credential_builder(ApolloCredentials),
        ),
        "arcads": ProviderCredentialSpec(
            family="arcads",
            description="Arcads API credentials.",
            fields=(
                ProviderCredentialFieldSpec("client_id", "Arcads client id."),
                ProviderCredentialFieldSpec("client_secret", "Arcads client secret."),
            ),
            builder=build_dataclass_credential_builder(ArcadsCredentials),
        ),
        "attio": ProviderCredentialSpec(
            family="attio",
            description="Attio API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "Attio API key."),),
            builder=build_dataclass_credential_builder(AttioCredentials),
        ),
        "coresignal": ProviderCredentialSpec(
            family="coresignal",
            description="Coresignal API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "Coresignal API key."),),
            builder=build_dataclass_credential_builder(CoreSignalCredentials),
        ),
        "creatify": ProviderCredentialSpec(
            family="creatify",
            description="Creatify API credentials.",
            fields=(
                ProviderCredentialFieldSpec("api_id", "Creatify API id."),
                ProviderCredentialFieldSpec("api_key", "Creatify API key."),
            ),
            builder=build_dataclass_credential_builder(CreatifyCredentials),
        ),
        "exa": ProviderCredentialSpec(
            family="exa",
            description="Exa API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "Exa API key."),),
            builder=build_dataclass_credential_builder(ExaCredentials),
        ),
        "expandi": ProviderCredentialSpec(
            family="expandi",
            description="Expandi API credentials.",
            fields=(
                ProviderCredentialFieldSpec("api_key", "Expandi API key."),
                ProviderCredentialFieldSpec("api_secret", "Expandi API secret."),
            ),
            builder=build_dataclass_credential_builder(ExpandiCredentials),
        ),
        "google_drive": ProviderCredentialSpec(
            family="google_drive",
            description="Google Drive OAuth credentials.",
            fields=(
                ProviderCredentialFieldSpec("client_id", "Google OAuth client id."),
                ProviderCredentialFieldSpec("client_secret", "Google OAuth client secret."),
                ProviderCredentialFieldSpec("refresh_token", "Google OAuth refresh token."),
            ),
            builder=build_dataclass_credential_builder(GoogleDriveCredentials),
        ),
        "inboxapp": ProviderCredentialSpec(
            family="inboxapp",
            description="InboxApp API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "InboxApp API key."),),
            builder=build_dataclass_credential_builder(InboxAppCredentials),
        ),
        "instantly": ProviderCredentialSpec(
            family="instantly",
            description="Instantly API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "Instantly API key."),),
            builder=build_dataclass_credential_builder(InstantlyCredentials),
        ),
        "leadiq": ProviderCredentialSpec(
            family="leadiq",
            description="LeadIQ API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "LeadIQ API key."),),
            builder=build_dataclass_credential_builder(LeadIQCredentials),
        ),
        "lemlist": ProviderCredentialSpec(
            family="lemlist",
            description="Lemlist API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "Lemlist API key."),),
            builder=build_dataclass_credential_builder(LemlistCredentials),
        ),
        "lusha": ProviderCredentialSpec(
            family="lusha",
            description="Lusha API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "Lusha API key."),),
            builder=build_dataclass_credential_builder(LushaCredentials),
        ),
        "outreach": ProviderCredentialSpec(
            family="outreach",
            description="Outreach API credentials.",
            fields=(ProviderCredentialFieldSpec("access_token", "Outreach access token."),),
            builder=build_dataclass_credential_builder(OutreachCredentials),
        ),
        "paperclip": ProviderCredentialSpec(
            family="paperclip",
            description="Paperclip API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "Paperclip API key."),),
            builder=build_dataclass_credential_builder(PaperclipCredentials),
        ),
        "peopledatalabs": ProviderCredentialSpec(
            family="peopledatalabs",
            description="People Data Labs API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "People Data Labs API key."),),
            builder=build_dataclass_credential_builder(PeopleDataLabsCredentials),
        ),
        "phantombuster": ProviderCredentialSpec(
            family="phantombuster",
            description="PhantomBuster API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "PhantomBuster API key."),),
            builder=build_dataclass_credential_builder(PhantomBusterCredentials),
        ),
        "proxycurl": ProviderCredentialSpec(
            family="proxycurl",
            description="Proxycurl API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "Proxycurl API key."),),
            builder=build_dataclass_credential_builder(ProxycurlCredentials),
        ),
        "resend": ProviderCredentialSpec(
            family="resend",
            description="Resend API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "Resend API key."),),
            builder=build_dataclass_credential_builder(ResendCredentials),
        ),
        "salesforge": ProviderCredentialSpec(
            family="salesforge",
            description="Salesforge API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "Salesforge API key."),),
            builder=build_dataclass_credential_builder(SalesforgeCredentials),
        ),
        "serper": ProviderCredentialSpec(
            family="serper",
            description="Serper API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "Serper API key."),),
            builder=build_dataclass_credential_builder(SerperCredentials),
        ),
        "smartlead": ProviderCredentialSpec(
            family="smartlead",
            description="Smartlead API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "Smartlead API key."),),
            builder=build_dataclass_credential_builder(SmartleadCredentials),
        ),
        "snovio": ProviderCredentialSpec(
            family="snovio",
            description="Snov.io API credentials.",
            fields=(
                ProviderCredentialFieldSpec("client_id", "Snov.io client id."),
                ProviderCredentialFieldSpec("client_secret", "Snov.io client secret."),
            ),
            builder=build_dataclass_credential_builder(SnovioCredentials),
        ),
        "zerobounce": ProviderCredentialSpec(
            family="zerobounce",
            description="ZeroBounce API credentials.",
            fields=(ProviderCredentialFieldSpec("api_key", "ZeroBounce API key."),),
            builder=build_dataclass_credential_builder(ZeroBounceCredentials),
        ),
        "zoominfo": ProviderCredentialSpec(
            family="zoominfo",
            description="ZoomInfo API credentials.",
            fields=(
                ProviderCredentialFieldSpec("username", "ZoomInfo username."),
                ProviderCredentialFieldSpec("password", "ZoomInfo password."),
            ),
            builder=build_dataclass_credential_builder(ZoomInfoCredentials),
        ),
    }
)


__all__ = ["PROVIDER_CREDENTIAL_SPECS"]
