"""Static catalog metadata for the Harnessiq toolset.

Declares ``ToolEntry`` — the lightweight metadata record for each tool — and
provides the static entries and factory-dispatch tables that ``ToolsetRegistry``
uses to resolve ``RegisteredTool`` objects on demand.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from harnessiq.shared.tools import RegisteredTool

_BuiltinFactory = Callable[[], tuple[RegisteredTool, ...]]


@dataclass(frozen=True, slots=True)
class ToolEntry:
    """Lightweight metadata record for a single tool in the Harnessiq catalog.

    Attributes:
        key: Unique tool identifier in ``namespace.name`` format.
        name: Short human-readable name (snake_case).
        description: One-sentence summary of what the tool does.
        family: The tool's family grouping — derived from the key namespace
            prefix (everything before the first ``.``).
        requires_credentials: ``True`` if the tool connects to an external API
            and cannot be instantiated without a credentials object.
    """

    key: str
    name: str
    description: str
    family: str
    requires_credentials: bool


# ---------------------------------------------------------------------------
# Built-in family factories
# ---------------------------------------------------------------------------
# Maps family name → zero-argument callable that returns all tools in that
# family.  Imports are deferred to avoid circular dependencies and to keep
# module load time low.

def _builtin_core() -> tuple[RegisteredTool, ...]:
    from harnessiq.shared.tools import ADD_NUMBERS, ECHO_TEXT
    from harnessiq.tools.builtin import BUILTIN_TOOLS
    core_keys = frozenset({ECHO_TEXT, ADD_NUMBERS})
    return tuple(t for t in BUILTIN_TOOLS if t.key in core_keys)


def _builtin_context() -> tuple[RegisteredTool, ...]:
    from harnessiq.tools.context_compaction import create_context_compaction_tools
    return create_context_compaction_tools()


def _builtin_general_purpose() -> tuple[RegisteredTool, ...]:
    # Returns text.*, records.*, and control.* tools — grouped in the registry
    # by their actual key prefix, not by this factory's entry key.
    from harnessiq.tools.general_purpose import create_general_purpose_tools
    return create_general_purpose_tools()


def _builtin_prompt() -> tuple[RegisteredTool, ...]:
    from harnessiq.tools.prompting import create_prompt_tools
    return create_prompt_tools()


def _builtin_filesystem() -> tuple[RegisteredTool, ...]:
    from harnessiq.tools.filesystem import create_filesystem_tools
    return create_filesystem_tools()


def _builtin_instagram() -> tuple[RegisteredTool, ...]:
    from harnessiq.tools.instagram import create_instagram_tools
    return create_instagram_tools()


def _builtin_reason() -> tuple[RegisteredTool, ...]:
    from harnessiq.tools.reasoning.core import create_injectable_reasoning_tools
    return create_injectable_reasoning_tools()


def _builtin_reasoning() -> tuple[RegisteredTool, ...]:
    from harnessiq.tools.reasoning.lenses import create_reasoning_tools
    return create_reasoning_tools()


# Ordered sequence of built-in factory callables.
# Tools from each factory are grouped in the registry by their actual key
# prefix (e.g. _builtin_general_purpose returns text.*, records.*, control.*
# which end up in three separate families).
BUILTIN_FAMILY_FACTORIES: tuple[_BuiltinFactory, ...] = (
    _builtin_core,
    _builtin_context,
    _builtin_general_purpose,
    _builtin_prompt,
    _builtin_filesystem,
    _builtin_instagram,
    _builtin_reason,
    _builtin_reasoning,
)


# ---------------------------------------------------------------------------
# Provider tool entries (static metadata — no credentials required to list)
# ---------------------------------------------------------------------------

PROVIDER_ENTRIES: tuple[ToolEntry, ...] = (
    ToolEntry(
        key="attio.request",
        name="attio_request",
        description="Execute authenticated Attio CRM REST API operations.",
        family="attio",
        requires_credentials=True,
    ),
    ToolEntry(
        key="apollo.request",
        name="apollo_request",
        description="Execute authenticated Apollo.io B2B sales intelligence and engagement API operations.",
        family="apollo",
        requires_credentials=True,
    ),
    ToolEntry(
        key="arcads.request",
        name="arcads_request",
        description="Execute authenticated Arcads AI advertising video creation API operations.",
        family="arcads",
        requires_credentials=True,
    ),
    ToolEntry(
        key="arxiv.request",
        name="arxiv_request",
        description=(
            "Execute arXiv academic paper search and retrieval API operations "
            "(no credentials required)."
        ),
        family="arxiv",
        requires_credentials=False,
    ),
    ToolEntry(
        key="coresignal.request",
        name="coresignal_request",
        description="Execute authenticated Coresignal professional network data API operations.",
        family="coresignal",
        requires_credentials=True,
    ),
    ToolEntry(
        key="creatify.request",
        name="creatify_request",
        description="Execute authenticated Creatify AI video creation API operations.",
        family="creatify",
        requires_credentials=True,
    ),
    ToolEntry(
        key="exa.request",
        name="exa_request",
        description="Execute authenticated Exa neural search API operations.",
        family="exa",
        requires_credentials=True,
    ),
    ToolEntry(
        key="expandi.request",
        name="expandi_request",
        description="Execute authenticated Expandi LinkedIn outreach automation API operations.",
        family="expandi",
        requires_credentials=True,
    ),
    ToolEntry(
        key="instantly.request",
        name="instantly_request",
        description="Execute authenticated Instantly cold email platform API operations.",
        family="instantly",
        requires_credentials=True,
    ),
    ToolEntry(
        key="inboxapp.request",
        name="inboxapp_request",
        description="Execute authenticated InboxApp messaging and workflow API operations.",
        family="inboxapp",
        requires_credentials=True,
    ),
    ToolEntry(
        key="lusha.request",
        name="lusha_request",
        description="Execute authenticated Lusha B2B contact and company intelligence API operations.",
        family="lusha",
        requires_credentials=True,
    ),
    ToolEntry(
        key="leadiq.request",
        name="leadiq_request",
        description="Execute authenticated LeadIQ contact intelligence API operations (GraphQL).",
        family="leadiq",
        requires_credentials=True,
    ),
    ToolEntry(
        key="lemlist.request",
        name="lemlist_request",
        description="Execute authenticated Lemlist B2B outreach platform API operations.",
        family="lemlist",
        requires_credentials=True,
    ),
    ToolEntry(
        key="outreach.request",
        name="outreach_request",
        description="Execute authenticated Outreach sales engagement platform API operations.",
        family="outreach",
        requires_credentials=True,
    ),
    ToolEntry(
        key="paperclip.request",
        name="paperclip_request",
        description="Execute authenticated Paperclip control-plane API operations for companies, agents, issues, approvals, activity, and costs.",
        family="paperclip",
        requires_credentials=True,
    ),
    ToolEntry(
        key="peopledatalabs.request",
        name="peopledatalabs_request",
        description="Execute authenticated People Data Labs data enrichment API operations.",
        family="peopledatalabs",
        requires_credentials=True,
    ),
    ToolEntry(
        key="phantombuster.request",
        name="phantombuster_request",
        description="Execute authenticated PhantomBuster browser automation API operations.",
        family="phantombuster",
        requires_credentials=True,
    ),
    ToolEntry(
        key="proxycurl.request",
        name="proxycurl_request",
        description=(
            "Execute authenticated Proxycurl LinkedIn data API operations. "
            "Note: Proxycurl was deprecated January 2025."
        ),
        family="proxycurl",
        requires_credentials=True,
    ),
    ToolEntry(
        key="resend.request",
        name="resend_request",
        description="Execute authenticated Resend transactional email API operations.",
        family="resend",
        requires_credentials=True,
    ),
    ToolEntry(
        key="smartlead.request",
        name="smartlead_request",
        description="Execute authenticated Smartlead cold email outreach and warm-up API operations.",
        family="smartlead",
        requires_credentials=True,
    ),
    ToolEntry(
        key="salesforge.request",
        name="salesforge_request",
        description="Execute authenticated Salesforge cold email automation API operations.",
        family="salesforge",
        requires_credentials=True,
    ),
    ToolEntry(
        key="serper.request",
        name="serper_request",
        description="Execute authenticated Serper Google search API operations.",
        family="serper",
        requires_credentials=True,
    ),
    ToolEntry(
        key="snovio.request",
        name="snovio_request",
        description="Execute authenticated Snov.io email intelligence API operations (OAuth2).",
        family="snovio",
        requires_credentials=True,
    ),
    ToolEntry(
        key="zerobounce.request",
        name="zerobounce_request",
        description="Execute authenticated ZeroBounce email validation and intelligence API operations.",
        family="zerobounce",
        requires_credentials=True,
    ),
    ToolEntry(
        key="zoominfo.request",
        name="zoominfo_request",
        description="Execute authenticated ZoomInfo B2B intelligence API operations (JWT auth).",
        family="zoominfo",
        requires_credentials=True,
    ),
)

# Key → entry index for fast provider lookup.
PROVIDER_ENTRY_INDEX: dict[str, ToolEntry] = {e.key: e for e in PROVIDER_ENTRIES}

# ---------------------------------------------------------------------------
# Provider factory dispatch table
# ---------------------------------------------------------------------------
# Maps family name → (module_path, function_name).  Imported lazily at
# resolve time so the catalog can be loaded without pulling in all provider
# HTTP clients and credentials types.

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


__all__ = [
    "BUILTIN_FAMILY_FACTORIES",
    "PROVIDER_ENTRIES",
    "PROVIDER_ENTRY_INDEX",
    "PROVIDER_FACTORY_MAP",
    "ToolEntry",
]
