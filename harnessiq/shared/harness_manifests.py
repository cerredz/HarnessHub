"""Registry helpers for the built-in Harnessiq harness manifests."""

from __future__ import annotations

from collections.abc import Iterable
from types import MappingProxyType

from harnessiq.shared.exa_outreach import EXA_OUTREACH_HARNESS_MANIFEST
from harnessiq.shared.instagram import INSTAGRAM_HARNESS_MANIFEST
from harnessiq.shared.knowt import KNOWT_HARNESS_MANIFEST
from harnessiq.shared.leads import LEADS_HARNESS_MANIFEST
from harnessiq.shared.linkedin import LINKEDIN_HARNESS_MANIFEST
from harnessiq.shared.prospecting import PROSPECTING_HARNESS_MANIFEST
from harnessiq.utils.harness_manifest.registry import (
    load_entrypoint_manifests,
    register_manifest,
    resolve_registered_manifest,
)

from .harness_manifest import HarnessManifest

_BUILTIN_HARNESS_MANIFESTS: tuple[HarnessManifest, ...] = (
    EXA_OUTREACH_HARNESS_MANIFEST,
    INSTAGRAM_HARNESS_MANIFEST,
    KNOWT_HARNESS_MANIFEST,
    LEADS_HARNESS_MANIFEST,
    LINKEDIN_HARNESS_MANIFEST,
    PROSPECTING_HARNESS_MANIFEST,
)

_HARNESS_MANIFESTS: dict[str, HarnessManifest] = {}
_HARNESS_MANIFESTS_BY_AGENT_NAME: dict[str, HarnessManifest] = {}
_HARNESS_MANIFESTS_BY_CLI_COMMAND: dict[str, HarnessManifest] = {}
_ENTRYPOINTS_LOADED = False


def _register_manifest(manifest: HarnessManifest) -> HarnessManifest:
    return register_manifest(
        manifest,
        manifests=_HARNESS_MANIFESTS,
        manifests_by_agent_name=_HARNESS_MANIFESTS_BY_AGENT_NAME,
        manifests_by_cli_command=_HARNESS_MANIFESTS_BY_CLI_COMMAND,
    )


for _manifest in _BUILTIN_HARNESS_MANIFESTS:
    _register_manifest(_manifest)


HARNESS_MANIFESTS = MappingProxyType(_HARNESS_MANIFESTS)
HARNESS_MANIFESTS_BY_AGENT_NAME = MappingProxyType(_HARNESS_MANIFESTS_BY_AGENT_NAME)
HARNESS_MANIFESTS_BY_CLI_COMMAND = MappingProxyType(_HARNESS_MANIFESTS_BY_CLI_COMMAND)


def register_harness_manifest(manifest: HarnessManifest) -> HarnessManifest:
    """Register one additional harness manifest at runtime."""
    return _register_manifest(manifest)


def register_harness_manifests(manifests: Iterable[HarnessManifest]) -> tuple[HarnessManifest, ...]:
    """Register multiple harness manifests at runtime."""
    return tuple(register_harness_manifest(manifest) for manifest in manifests)


def _ensure_entrypoints_loaded() -> None:
    global _ENTRYPOINTS_LOADED
    if _ENTRYPOINTS_LOADED:
        return
    _ENTRYPOINTS_LOADED = True
    register_harness_manifests(load_entrypoint_manifests())


def list_harness_manifests() -> tuple[HarnessManifest, ...]:
    """Return the built-in harness manifests in deterministic order."""
    _ensure_entrypoints_loaded()
    return tuple(_HARNESS_MANIFESTS.values())


def get_harness_manifest(query: str) -> HarnessManifest:
    """Resolve a harness manifest by manifest id, agent name, or CLI command."""
    _ensure_entrypoints_loaded()
    return resolve_registered_manifest(
        query,
        manifests=HARNESS_MANIFESTS,
        manifests_by_agent_name=HARNESS_MANIFESTS_BY_AGENT_NAME,
        manifests_by_cli_command=HARNESS_MANIFESTS_BY_CLI_COMMAND,
    )


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
    "register_harness_manifest",
    "register_harness_manifests",
]
