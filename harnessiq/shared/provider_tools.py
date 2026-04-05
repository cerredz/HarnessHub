"""Static provider-tool factory metadata shared across runtime surfaces."""

from __future__ import annotations

PROVIDER_FACTORY_MAP: dict[str, tuple[str, str]] = {
    "attio": ("harnessiq.tools.attio", "create_attio_tools"),
    "apollo": ("harnessiq.tools.apollo", "create_apollo_tools"),
    "arcads": ("harnessiq.tools.arcads", "create_arcads_tools"),
    "arxiv": ("harnessiq.tools.arxiv", "create_arxiv_tools"),
    "coresignal": ("harnessiq.tools.coresignal", "create_coresignal_tools"),
    "creatify": ("harnessiq.tools.creatify", "create_creatify_tools"),
    "exa": ("harnessiq.tools.exa", "create_exa_tools"),
    "expandi": ("harnessiq.tools.expandi", "create_expandi_tools"),
    "instantly": ("harnessiq.tools.instantly", "create_instantly_tools"),
    "inboxapp": ("harnessiq.tools.inboxapp", "create_inboxapp_tools"),
    "leadiq": ("harnessiq.tools.leadiq", "create_leadiq_tools"),
    "lusha": ("harnessiq.tools.lusha", "create_lusha_tools"),
    "lemlist": ("harnessiq.tools.lemlist", "create_lemlist_tools"),
    "outreach": ("harnessiq.tools.outreach", "create_outreach_tools"),
    "paperclip": ("harnessiq.tools.paperclip", "create_paperclip_tools"),
    "peopledatalabs": ("harnessiq.tools.peopledatalabs", "create_peopledatalabs_tools"),
    "phantombuster": ("harnessiq.tools.phantombuster", "create_phantombuster_tools"),
    "proxycurl": ("harnessiq.tools.proxycurl", "create_proxycurl_tools"),
    "resend": ("harnessiq.tools.resend", "create_resend_tools"),
    "salesforge": ("harnessiq.tools.salesforge", "create_salesforge_tools"),
    "serper": ("harnessiq.tools.serper", "create_serper_tools"),
    "smartlead": ("harnessiq.tools.smartlead", "create_smartlead_tools"),
    "snovio": ("harnessiq.tools.snovio", "create_snovio_tools"),
    "zerobounce": ("harnessiq.tools.zerobounce", "create_zerobounce_tools"),
    "zoominfo": ("harnessiq.tools.zoominfo", "create_zoominfo_tools"),
}

__all__ = ["PROVIDER_FACTORY_MAP"]
