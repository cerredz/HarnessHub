"""Static catalog metadata for the Harnessiq toolset.

Declares ``ToolEntry`` — the lightweight metadata record for each tool — and
provides the static entries and factory-dispatch tables that ``ToolsetRegistry``
uses to resolve ``RegisteredTool`` objects on demand.
"""

from __future__ import annotations

from dataclasses import dataclass


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

def _builtin_core():  # type: ignore[return]
    from harnessiq.tools.builtin import BUILTIN_TOOLS
    return tuple(t for t in BUILTIN_TOOLS if t.key.startswith("core."))


def _builtin_context():  # type: ignore[return]
    from harnessiq.tools.context_compaction import create_context_compaction_tools
    return create_context_compaction_tools()


def _builtin_text_records_control():  # type: ignore[return]
    from harnessiq.tools.general_purpose import create_general_purpose_tools
    return create_general_purpose_tools()


def _builtin_prompt():  # type: ignore[return]
    from harnessiq.tools.prompting import create_prompt_tools
    return create_prompt_tools()


def _builtin_filesystem():  # type: ignore[return]
    from harnessiq.tools.filesystem import create_filesystem_tools
    return create_filesystem_tools()


def _builtin_reason():  # type: ignore[return]
    from harnessiq.tools.reasoning.core import create_reasoning_tools
    return create_reasoning_tools()


def _builtin_reasoning():  # type: ignore[return]
    from harnessiq.tools.reasoning.lenses import create_reasoning_tools
    return create_reasoning_tools()


# Ordered mapping of family name → factory callable.
# The families that span multiple namespaces (text/records/control all come
# from create_general_purpose_tools) are handled by _load_builtin_tools()
# in the registry, which groups tools by key prefix after calling each factory.
BUILTIN_FAMILY_FACTORIES: dict[str, object] = {
    "core": _builtin_core,
    "context": _builtin_context,
    # text, records, control — all from general_purpose; keyed separately below
    "general": _builtin_text_records_control,
    "prompt": _builtin_prompt,
    "filesystem": _builtin_filesystem,
    "reason": _builtin_reason,
    "reasoning": _builtin_reasoning,
}


# ---------------------------------------------------------------------------
# Provider tool entries (static metadata — no credentials required to list)
# ---------------------------------------------------------------------------

PROVIDER_ENTRIES: tuple[ToolEntry, ...] = (
    ToolEntry(
        key="arcads.request",
        name="arcads_request",
        description="Execute authenticated Arcads AI advertising video creation API operations.",
        family="arcads",
        requires_credentials=True,
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
        key="instantly.request",
        name="instantly_request",
        description="Execute authenticated Instantly cold email platform API operations.",
        family="instantly",
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
        key="salesforge.request",
        name="salesforge_request",
        description="Execute authenticated Salesforge cold email automation API operations.",
        family="salesforge",
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
    "arcads": ("harnessiq.tools.arcads", "create_arcads_tools"),
    "coresignal": ("harnessiq.tools.coresignal", "create_coresignal_tools"),
    "creatify": ("harnessiq.tools.creatify", "create_creatify_tools"),
    "exa": ("harnessiq.tools.exa", "create_exa_tools"),
    "instantly": ("harnessiq.tools.instantly", "create_instantly_tools"),
    "leadiq": ("harnessiq.tools.leadiq", "create_leadiq_tools"),
    "lemlist": ("harnessiq.tools.lemlist", "create_lemlist_tools"),
    "outreach": ("harnessiq.tools.outreach", "create_outreach_tools"),
    "peopledatalabs": ("harnessiq.tools.peopledatalabs", "create_peopledatalabs_tools"),
    "phantombuster": ("harnessiq.tools.phantombuster", "create_phantombuster_tools"),
    "proxycurl": ("harnessiq.tools.proxycurl", "create_proxycurl_tools"),
    "resend": ("harnessiq.tools.resend", "create_resend_tools"),
    "salesforge": ("harnessiq.tools.salesforge", "create_salesforge_tools"),
    "snovio": ("harnessiq.tools.snovio", "create_snovio_tools"),
    "zoominfo": ("harnessiq.tools.zoominfo", "create_zoominfo_tools"),
}


__all__ = [
    "BUILTIN_FAMILY_FACTORIES",
    "PROVIDER_ENTRIES",
    "PROVIDER_ENTRY_INDEX",
    "PROVIDER_FACTORY_MAP",
    "ToolEntry",
]
