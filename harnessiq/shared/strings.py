"""Shared string constant enums for provider names and model identifiers."""

from __future__ import annotations

from enum import StrEnum


class ProviderName(StrEnum):
    """Canonical provider name constants used across the SDK.

    Because ``ProviderName`` inherits from ``str``, every member compares
    equal to its bare-string equivalent (e.g. ``ProviderName.OPENAI == "openai"``
    is ``True``), so existing string-based comparisons and test assertions
    require no changes.
    """

    # --- Model providers ---
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GROK = "grok"
    GEMINI = "gemini"

    # --- Service providers ---
    APOLLO = "apollo"
    ARCADS = "arcads"
    ARXIV = "arxiv"
    ATTIO = "attio"
    BROWSER_USE = "browser_use"
    CORESIGNAL = "coresignal"
    CREATIFY = "creatify"
    EXA = "exa"
    EXPANDI = "expandi"
    GOOGLE_DRIVE = "google_drive"
    HUNTER = "hunter"
    INBOXAPP = "inboxapp"
    INSTANTLY = "instantly"
    LEADIQ = "leadiq"
    LEMLIST = "lemlist"
    LUSHA = "lusha"
    OUTREACH = "outreach"
    PAPERCLIP = "paperclip"
    PEOPLEDATALABS = "peopledatalabs"
    PHANTOMBUSTER = "phantombuster"
    PROXYCURL = "proxycurl"
    RESEND = "resend"
    SALESFORGE = "salesforge"
    SERPER = "serper"
    SMARTLEAD = "smartlead"
    SNOVIO = "snovio"
    ZEROBOUNCE = "zerobounce"
    ZOOMINFO = "zoominfo"

    # --- Fallback ---
    UNKNOWN = "provider"


__all__ = ["ProviderName"]
