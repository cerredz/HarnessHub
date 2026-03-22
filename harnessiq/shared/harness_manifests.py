"""Registry helpers for the built-in Harnessiq harness manifests."""

from __future__ import annotations

from collections.abc import Iterable
from importlib import metadata
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

_HARNESS_MANIFESTS: dict[str, HarnessManifest] = {}
_HARNESS_MANIFESTS_BY_AGENT_NAME: dict[str, HarnessManifest] = {}
_HARNESS_MANIFESTS_BY_CLI_COMMAND: dict[str, HarnessManifest] = {}
_ENTRYPOINTS_LOADED = False


def _register_manifest(manifest: HarnessManifest) -> HarnessManifest:
    if manifest.manifest_id in _HARNESS_MANIFESTS:
        raise ValueError(f"Duplicate harness manifest id '{manifest.manifest_id}'.")
    if manifest.agent_name in _HARNESS_MANIFESTS_BY_AGENT_NAME:
        raise ValueError(f"Duplicate harness agent name '{manifest.agent_name}'.")
    if manifest.cli_command is not None and manifest.cli_command in _HARNESS_MANIFESTS_BY_CLI_COMMAND:
        raise ValueError(f"Duplicate harness CLI command '{manifest.cli_command}'.")
    _HARNESS_MANIFESTS[manifest.manifest_id] = manifest
    _HARNESS_MANIFESTS_BY_AGENT_NAME[manifest.agent_name] = manifest
    if manifest.cli_command is not None:
        _HARNESS_MANIFESTS_BY_CLI_COMMAND[manifest.cli_command] = manifest
    return manifest


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
    try:
        entry_points = metadata.entry_points(group="harnessiq.harnesses")
    except TypeError:  # pragma: no cover - compatibility fallback
        entry_points = metadata.entry_points().get("harnessiq.harnesses", [])
    for entry_point in entry_points:
        loaded = entry_point.load()
        if isinstance(loaded, HarnessManifest):
            register_harness_manifest(loaded)
            continue
        if callable(loaded):
            produced = loaded()
            if isinstance(produced, HarnessManifest):
                register_harness_manifest(produced)
                continue
            if isinstance(produced, Iterable):
                register_harness_manifests(
                    manifest for manifest in produced if isinstance(manifest, HarnessManifest)
                )
                continue
        raise TypeError(
            f"Harness entry point '{entry_point.name}' must resolve to a HarnessManifest, "
            "a callable returning one, or an iterable of HarnessManifest instances."
        )


def list_harness_manifests() -> tuple[HarnessManifest, ...]:
    """Return the built-in harness manifests in deterministic order."""
    _ensure_entrypoints_loaded()
    return tuple(_HARNESS_MANIFESTS.values())


def get_harness_manifest(query: str) -> HarnessManifest:
    """Resolve a harness manifest by manifest id, agent name, or CLI command."""
    _ensure_entrypoints_loaded()
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
    "register_harness_manifest",
    "register_harness_manifests",
]
