"""Registry helpers for the built-in Harnessiq harness manifests."""

from __future__ import annotations

from types import MappingProxyType

from harnessiq.shared.exa_outreach import EXA_OUTREACH_HARNESS_MANIFEST
from harnessiq.shared.instagram import INSTAGRAM_HARNESS_MANIFEST
from harnessiq.shared.knowt import KNOWT_HARNESS_MANIFEST
from harnessiq.shared.leads import LEADS_HARNESS_MANIFEST
from harnessiq.shared.linkedin import LINKEDIN_HARNESS_MANIFEST
from harnessiq.shared.prospecting import PROSPECTING_HARNESS_MANIFEST

from .harness_manifest import HarnessManifest

_BUILTIN_HARNESS_MANIFESTS: tuple[HarnessManifest, ...] = (
    EXA_OUTREACH_HARNESS_MANIFEST,
    INSTAGRAM_HARNESS_MANIFEST,
    KNOWT_HARNESS_MANIFEST,
    LEADS_HARNESS_MANIFEST,
    LINKEDIN_HARNESS_MANIFEST,
    PROSPECTING_HARNESS_MANIFEST,
)

HARNESS_MANIFESTS = MappingProxyType(
    {manifest.manifest_id: manifest for manifest in _BUILTIN_HARNESS_MANIFESTS}
)
HARNESS_MANIFESTS_BY_AGENT_NAME = MappingProxyType(
    {manifest.agent_name: manifest for manifest in _BUILTIN_HARNESS_MANIFESTS}
)
HARNESS_MANIFESTS_BY_CLI_COMMAND = MappingProxyType(
    {
        manifest.cli_command: manifest
        for manifest in _BUILTIN_HARNESS_MANIFESTS
        if manifest.cli_command is not None
    }
)


def list_harness_manifests() -> tuple[HarnessManifest, ...]:
    """Return the built-in harness manifests in deterministic order."""
    return _BUILTIN_HARNESS_MANIFESTS


def get_harness_manifest(query: str) -> HarnessManifest:
    """Resolve a harness manifest by manifest id, agent name, or CLI command."""
    normalized_query = query.strip()
    if normalized_query in HARNESS_MANIFESTS:
        return HARNESS_MANIFESTS[normalized_query]
    if normalized_query in HARNESS_MANIFESTS_BY_AGENT_NAME:
        return HARNESS_MANIFESTS_BY_AGENT_NAME[normalized_query]
    if normalized_query in HARNESS_MANIFESTS_BY_CLI_COMMAND:
        return HARNESS_MANIFESTS_BY_CLI_COMMAND[normalized_query]
    raise KeyError(f"No harness manifest exists for '{query}'.")


__all__ = [
    "EXA_OUTREACH_HARNESS_MANIFEST",
    "HARNESS_MANIFESTS",
    "HARNESS_MANIFESTS_BY_AGENT_NAME",
    "HARNESS_MANIFESTS_BY_CLI_COMMAND",
    "INSTAGRAM_HARNESS_MANIFEST",
    "KNOWT_HARNESS_MANIFEST",
    "LEADS_HARNESS_MANIFEST",
    "LINKEDIN_HARNESS_MANIFEST",
    "PROSPECTING_HARNESS_MANIFEST",
    "get_harness_manifest",
    "list_harness_manifests",
]
