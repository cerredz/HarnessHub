"""Shared provider constants and aliases."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

ProviderName = Literal["anthropic", "openai", "grok", "gemini"]
ProviderMessageRole = Literal["system", "user", "assistant"]
RequestPayload = dict[str, Any]


class ProviderMessage(TypedDict):
    """Provider-agnostic chat message shape."""

    role: ProviderMessageRole
    content: str


SUPPORTED_PROVIDERS: tuple[ProviderName, ...] = ("anthropic", "openai", "grok", "gemini")
ALLOWED_MESSAGE_ROLES: frozenset[ProviderMessageRole] = frozenset({"system", "user", "assistant"})
GEMINI_ROLE_MAP: dict[ProviderMessageRole, str] = {
    "user": "user",
    "assistant": "model",
    "system": "user",
}

ANTHROPIC_DEFAULT_BASE_URL = "https://api.anthropic.com"
ANTHROPIC_DEFAULT_API_VERSION = "2023-06-01"
APOLLO_DEFAULT_BASE_URL = "https://api.apollo.io/api/v1"
ARCADS_DEFAULT_BASE_URL = "https://external-api.arcads.ai"
ARXIV_DEFAULT_BASE_URL = "https://export.arxiv.org"
ATTIO_DEFAULT_BASE_URL = "https://api.attio.com/v2"
CORESIGNAL_DEFAULT_BASE_URL = "https://api.coresignal.com/cdapi/v2"
CREATIFY_DEFAULT_BASE_URL = "https://api.creatify.ai"
EXA_DEFAULT_BASE_URL = "https://api.exa.ai"
EXPANDI_DEFAULT_BASE_URL = "https://api.liaufa.com/api/v1"
GEMINI_DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com"
GEMINI_DEFAULT_API_VERSION = "v1beta"
GROK_DEFAULT_BASE_URL = "https://api.x.ai"
INBOXAPP_DEFAULT_BASE_URL = "https://inboxapp.com/api/v1"
INSTANTLY_DEFAULT_BASE_URL = "https://api.instantly.ai/api/v2"
LEADIQ_DEFAULT_BASE_URL = "https://api.leadiq.com"
LEMLIST_DEFAULT_BASE_URL = "https://api.lemlist.com/api"
LUSHA_DEFAULT_BASE_URL = "https://api.lusha.com"
OPENAI_DEFAULT_BASE_URL = "https://api.openai.com"
OUTREACH_DEFAULT_BASE_URL = "https://api.outreach.io/api/v2"
PAPERCLIP_DEFAULT_BASE_URL = "http://localhost:3100/api"
PEOPLEDATALABS_DEFAULT_BASE_URL = "https://api.peopledatalabs.com/v5"
PHANTOMBUSTER_DEFAULT_BASE_URL = "https://api.phantombuster.com"
PROXYCURL_DEFAULT_BASE_URL = "https://nubela.co/proxycurl/api"
SALESFORGE_DEFAULT_BASE_URL = "https://api.salesforge.ai"
SERPER_DEFAULT_BASE_URL = "https://google.serper.dev"
SMARTLEAD_DEFAULT_BASE_URL = "https://server.smartlead.ai/api/v1"
SNOVIO_DEFAULT_BASE_URL = "https://api.snov.io"
ZEROBOUNCE_DEFAULT_BASE_URL = "https://api.zerobounce.net"
ZEROBOUNCE_DEFAULT_BULK_BASE_URL = "https://bulkapi.zerobounce.net"
ZOOMINFO_DEFAULT_BASE_URL = "https://api.zoominfo.com"

__all__ = [
    "ALLOWED_MESSAGE_ROLES",
    "ANTHROPIC_DEFAULT_API_VERSION",
    "ANTHROPIC_DEFAULT_BASE_URL",
    "APOLLO_DEFAULT_BASE_URL",
    "ARCADS_DEFAULT_BASE_URL",
    "ARXIV_DEFAULT_BASE_URL",
    "ATTIO_DEFAULT_BASE_URL",
    "CORESIGNAL_DEFAULT_BASE_URL",
    "CREATIFY_DEFAULT_BASE_URL",
    "EXA_DEFAULT_BASE_URL",
    "EXPANDI_DEFAULT_BASE_URL",
    "GEMINI_DEFAULT_API_VERSION",
    "GEMINI_DEFAULT_BASE_URL",
    "GEMINI_ROLE_MAP",
    "GROK_DEFAULT_BASE_URL",
    "INBOXAPP_DEFAULT_BASE_URL",
    "INSTANTLY_DEFAULT_BASE_URL",
    "LEADIQ_DEFAULT_BASE_URL",
    "LEMLIST_DEFAULT_BASE_URL",
    "LUSHA_DEFAULT_BASE_URL",
    "OPENAI_DEFAULT_BASE_URL",
    "OUTREACH_DEFAULT_BASE_URL",
    "PAPERCLIP_DEFAULT_BASE_URL",
    "PEOPLEDATALABS_DEFAULT_BASE_URL",
    "PHANTOMBUSTER_DEFAULT_BASE_URL",
    "ProviderMessage",
    "ProviderMessageRole",
    "ProviderName",
    "PROXYCURL_DEFAULT_BASE_URL",
    "RequestPayload",
    "SALESFORGE_DEFAULT_BASE_URL",
    "SERPER_DEFAULT_BASE_URL",
    "SMARTLEAD_DEFAULT_BASE_URL",
    "SNOVIO_DEFAULT_BASE_URL",
    "SUPPORTED_PROVIDERS",
    "ZEROBOUNCE_DEFAULT_BASE_URL",
    "ZEROBOUNCE_DEFAULT_BULK_BASE_URL",
    "ZOOMINFO_DEFAULT_BASE_URL",
]
