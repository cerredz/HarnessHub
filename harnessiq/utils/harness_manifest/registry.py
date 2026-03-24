"""Registry helpers for manifest lookup and entrypoint loading."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from importlib import metadata

from harnessiq.shared.harness_manifest import HarnessManifest


def register_manifest(
    manifest: HarnessManifest,
    *,
    manifests: dict[str, HarnessManifest],
    manifests_by_agent_name: dict[str, HarnessManifest],
    manifests_by_cli_command: dict[str, HarnessManifest],
) -> HarnessManifest:
    """Insert one manifest into the in-memory indexes while enforcing unique identifiers."""
    if manifest.manifest_id in manifests:
        raise ValueError(f"Duplicate harness manifest id '{manifest.manifest_id}'.")
    if manifest.agent_name in manifests_by_agent_name:
        raise ValueError(f"Duplicate harness agent name '{manifest.agent_name}'.")
    if manifest.cli_command is not None and manifest.cli_command in manifests_by_cli_command:
        raise ValueError(f"Duplicate harness CLI command '{manifest.cli_command}'.")
    manifests[manifest.manifest_id] = manifest
    manifests_by_agent_name[manifest.agent_name] = manifest
    if manifest.cli_command is not None:
        manifests_by_cli_command[manifest.cli_command] = manifest
    return manifest


def load_entrypoint_manifests() -> tuple[HarnessManifest, ...]:
    """Resolve runtime-discovered harness manifests from the `harnessiq.harnesses` entrypoint group."""
    try:
        entry_points = metadata.entry_points(group="harnessiq.harnesses")
    except TypeError:  # pragma: no cover - compatibility fallback
        entry_points = metadata.entry_points().get("harnessiq.harnesses", [])

    manifests: list[HarnessManifest] = []
    for entry_point in entry_points:
        loaded = entry_point.load()
        if isinstance(loaded, HarnessManifest):
            manifests.append(loaded)
            continue
        if callable(loaded):
            produced = loaded()
            if isinstance(produced, HarnessManifest):
                manifests.append(produced)
                continue
            if isinstance(produced, Iterable):
                manifests.extend(manifest for manifest in produced if isinstance(manifest, HarnessManifest))
                continue
        raise TypeError(
            f"Harness entry point '{entry_point.name}' must resolve to a HarnessManifest, "
            "a callable returning one, or an iterable of HarnessManifest instances."
        )
    return tuple(manifests)


def resolve_registered_manifest(
    query: str,
    *,
    manifests: Mapping[str, HarnessManifest],
    manifests_by_agent_name: Mapping[str, HarnessManifest],
    manifests_by_cli_command: Mapping[str, HarnessManifest],
) -> HarnessManifest:
    """Resolve one manifest by manifest id, agent name, or CLI command."""
    normalized_query = query.strip()
    if normalized_query in manifests:
        return manifests[normalized_query]
    if normalized_query in manifests_by_agent_name:
        return manifests_by_agent_name[normalized_query]
    if normalized_query in manifests_by_cli_command:
        return manifests_by_cli_command[normalized_query]
    raise KeyError(f"No harness manifest exists for '{query}'.")


__all__ = [
    "load_entrypoint_manifests",
    "register_manifest",
    "resolve_registered_manifest",
]
