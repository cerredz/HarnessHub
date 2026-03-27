"""Manifest-driven deployment-spec helpers for generic GCP-backed harness execution."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harnessiq.config import HarnessProfile, HarnessProfileIndexStore, HarnessProfileStore, HarnessRunSnapshot
from harnessiq.shared.harness_manifests import get_harness_manifest
from harnessiq.utils.path_serialization import deserialize_repo_path, serialize_repo_path

from .config import GcpAgentConfig

RUNTIME_MODULE = "harnessiq.providers.gcloud.runtime"
ENV_MANIFEST_ID = "HARNESSIQ_GCP_RUNTIME_MANIFEST_ID"
ENV_AGENT_NAME = "HARNESSIQ_GCP_RUNTIME_AGENT_NAME"
ENV_MEMORY_PATH = "HARNESSIQ_GCP_RUNTIME_MEMORY_PATH"
ENV_MODEL_SELECTION = "HARNESSIQ_GCP_RUNTIME_MODEL_SELECTION_JSON"
ENV_RUNTIME_PARAMETERS = "HARNESSIQ_GCP_RUNTIME_RUNTIME_PARAMETERS_JSON"
ENV_CUSTOM_PARAMETERS = "HARNESSIQ_GCP_RUNTIME_CUSTOM_PARAMETERS_JSON"
ENV_ADAPTER_ARGUMENTS = "HARNESSIQ_GCP_RUNTIME_ADAPTER_ARGUMENTS_JSON"
ENV_SINK_SPECS = "HARNESSIQ_GCP_RUNTIME_SINK_SPECS_JSON"
ENV_MEMORY_FILES = "HARNESSIQ_GCP_RUNTIME_MEMORY_FILES_JSON"
ENV_PROVIDER_FAMILIES = "HARNESSIQ_GCP_RUNTIME_PROVIDER_FAMILIES_JSON"
ENV_MAX_CYCLES = "HARNESSIQ_GCP_RUNTIME_MAX_CYCLES"


@dataclass(frozen=True, slots=True)
class GcpModelSelection:
    """One normalized model-selection contract for remote harness execution."""

    model_factory: str | None = None
    model: str | None = None
    model_profile: str | None = None

    def __post_init__(self) -> None:
        selected = [
            value
            for value in (self.model_factory, self.model, self.model_profile)
            if isinstance(value, str) and value.strip()
        ]
        if len(selected) != 1:
            raise ValueError("Exactly one of model_factory, model, or model_profile must be provided.")

    def as_dict(self) -> dict[str, str]:
        payload: dict[str, str] = {}
        if self.model_factory is not None:
            payload["model_factory"] = self.model_factory
        if self.model is not None:
            payload["model"] = self.model
        if self.model_profile is not None:
            payload["model_profile"] = self.model_profile
        return payload


@dataclass(frozen=True, slots=True)
class GcpMemoryEntry:
    """One declared durable memory entry from a harness manifest."""

    key: str
    relative_path: str
    kind: str
    format: str
    description: str

    def as_dict(self) -> dict[str, str]:
        return {
            "description": self.description,
            "format": self.format,
            "key": self.key,
            "kind": self.kind,
            "relative_path": self.relative_path,
        }


@dataclass(frozen=True, slots=True)
class GcpSecretReference:
    """One Secret Manager reference injected into a deployed job."""

    env_var: str
    secret_name: str

    def as_dict(self) -> dict[str, str]:
        return {
            "env_var": self.env_var,
            "secret_name": self.secret_name,
        }


@dataclass(frozen=True, slots=True)
class GcpDeploySpec:
    """Deterministic remote-run specification derived from manifests and saved profile state."""

    manifest_id: str
    display_name: str
    agent_name: str
    memory_path: str
    provider_families: tuple[str, ...]
    memory_entries: tuple[GcpMemoryEntry, ...]
    model_selection: GcpModelSelection
    max_cycles: int | None
    sink_specs: tuple[str, ...]
    adapter_arguments: dict[str, Any]
    runtime_parameters: dict[str, Any]
    custom_parameters: dict[str, Any]
    env_vars: dict[str, str]
    secret_references: tuple[GcpSecretReference, ...]
    remote_command: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "adapter_arguments": dict(self.adapter_arguments),
            "agent_name": self.agent_name,
            "custom_parameters": dict(self.custom_parameters),
            "display_name": self.display_name,
            "env_vars": dict(self.env_vars),
            "manifest_id": self.manifest_id,
            "max_cycles": self.max_cycles,
            "memory_entries": [entry.as_dict() for entry in self.memory_entries],
            "memory_path": self.memory_path,
            "model_selection": self.model_selection.as_dict(),
            "provider_families": list(self.provider_families),
            "remote_command": list(self.remote_command),
            "runtime_parameters": dict(self.runtime_parameters),
            "secret_references": [reference.as_dict() for reference in self.secret_references],
            "sink_specs": list(self.sink_specs),
        }


def derive_deploy_spec(
    config: GcpAgentConfig,
    *,
    repo_root: Path | str = ".",
) -> GcpDeploySpec:
    """Derive one JSON-safe deploy specification from a saved GCP agent config."""

    if config.manifest_id is None:
        raise ValueError("manifest_id must be set to derive a manifest-backed deploy spec.")

    resolved_repo_root = Path(repo_root).expanduser().resolve()
    manifest = get_harness_manifest(config.manifest_id)
    memory_path = _resolve_memory_path(config, repo_root=resolved_repo_root, manifest_default_root=manifest.resolved_default_memory_root)
    profile = _load_profile(config, memory_path=memory_path)
    snapshot = profile.last_run
    model_selection = _resolve_model_selection(config, snapshot=snapshot)
    runtime_parameters = manifest.resolve_runtime_parameters(
        _merge_mapping(profile.runtime_parameters, config.runtime_parameters)
    )
    custom_parameters = manifest.resolve_custom_parameters(
        _merge_mapping(profile.custom_parameters, config.custom_parameters)
    )
    adapter_arguments = _merge_mapping(snapshot.adapter_arguments if snapshot is not None else {}, config.adapter_arguments)
    sink_specs = tuple(config.sink_specs or (snapshot.sink_specs if snapshot is not None else ()))
    max_cycles = config.max_cycles if config.max_cycles is not None else (snapshot.max_cycles if snapshot is not None else None)
    serialized_memory_path = serialize_repo_path(memory_path, repo_root=resolved_repo_root)
    memory_entries = tuple(
        GcpMemoryEntry(
            key=entry.key,
            relative_path=entry.relative_path,
            kind=entry.kind,
            format=entry.format,
            description=entry.description,
        )
        for entry in manifest.memory_files
    )
    secret_references = tuple(
        GcpSecretReference(env_var=item["env_var"], secret_name=item["secret_name"])
        for item in config.secrets
    )
    env_vars = dict(config.env_vars)
    env_vars.update(
        {
            ENV_MANIFEST_ID: manifest.manifest_id,
            ENV_AGENT_NAME: config.agent_name,
            ENV_MEMORY_PATH: serialized_memory_path,
            ENV_MODEL_SELECTION: _dump_json(model_selection.as_dict()),
            ENV_RUNTIME_PARAMETERS: _dump_json(runtime_parameters),
            ENV_CUSTOM_PARAMETERS: _dump_json(custom_parameters),
            ENV_ADAPTER_ARGUMENTS: _dump_json(adapter_arguments),
            ENV_SINK_SPECS: _dump_json(list(sink_specs)),
            ENV_MEMORY_FILES: _dump_json([entry.as_dict() for entry in memory_entries]),
            ENV_PROVIDER_FAMILIES: _dump_json(list(manifest.provider_families)),
        }
    )
    if max_cycles is not None:
        env_vars[ENV_MAX_CYCLES] = str(max_cycles)

    remote_command = (
        "python",
        "-m",
        RUNTIME_MODULE,
        "--manifest-id",
        manifest.manifest_id,
        "--agent",
        config.agent_name,
        "--memory-path",
        serialized_memory_path,
    )
    return GcpDeploySpec(
        manifest_id=manifest.manifest_id,
        display_name=manifest.display_name,
        agent_name=config.agent_name,
        memory_path=serialized_memory_path,
        provider_families=manifest.provider_families,
        memory_entries=memory_entries,
        model_selection=model_selection,
        max_cycles=max_cycles,
        sink_specs=sink_specs,
        adapter_arguments=adapter_arguments,
        runtime_parameters=runtime_parameters,
        custom_parameters=custom_parameters,
        env_vars=env_vars,
        secret_references=secret_references,
        remote_command=remote_command,
    )


def _resolve_memory_path(
    config: GcpAgentConfig,
    *,
    repo_root: Path,
    manifest_default_root: str,
) -> Path:
    if config.memory_path is not None:
        return deserialize_repo_path(config.memory_path, repo_root=repo_root)

    records = HarnessProfileIndexStore(repo_root=repo_root).list(
        agent_name=config.agent_name,
        manifest_id=config.manifest_id,
    )
    if records:
        selected = sorted(
            records,
            key=lambda record: (
                record.updated_at,
                serialize_repo_path(record.memory_path, repo_root=repo_root),
            ),
        )[-1]
        return selected.memory_path

    default_root = deserialize_repo_path(manifest_default_root, repo_root=repo_root)
    return default_root / _slugify_agent_name(config.agent_name)


def _load_profile(config: GcpAgentConfig, *, memory_path: Path) -> HarnessProfile:
    store = HarnessProfileStore(memory_path)
    return store.load(manifest_id=str(config.manifest_id), agent_name=config.agent_name)


def _resolve_model_selection(
    config: GcpAgentConfig,
    *,
    snapshot: HarnessRunSnapshot | None,
) -> GcpModelSelection:
    if any(value is not None for value in (config.model_factory, config.model, config.model_profile)):
        return GcpModelSelection(
            model_factory=config.model_factory,
            model=config.model,
            model_profile=config.model_profile,
        )
    if snapshot is None:
        raise ValueError(
            "A manifest-backed deploy spec requires one model selection from the saved GCP config or the last harness run snapshot."
        )
    return GcpModelSelection(
        model_factory=snapshot.model_factory,
        model=snapshot.model,
        model_profile=snapshot.model_profile,
    )


def _merge_mapping(base: dict[str, Any] | None, override: dict[str, Any] | None) -> dict[str, Any]:
    payload = dict(base or {})
    payload.update(dict(override or {}))
    return payload


def _dump_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True)


def _slugify_agent_name(agent_name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", agent_name.strip()).strip("-")
    if not cleaned:
        raise ValueError("agent_name must contain at least one alphanumeric character.")
    return cleaned


__all__ = [
    "ENV_ADAPTER_ARGUMENTS",
    "ENV_AGENT_NAME",
    "ENV_CUSTOM_PARAMETERS",
    "ENV_MANIFEST_ID",
    "ENV_MAX_CYCLES",
    "ENV_MEMORY_FILES",
    "ENV_MEMORY_PATH",
    "ENV_MODEL_SELECTION",
    "ENV_PROVIDER_FAMILIES",
    "ENV_RUNTIME_PARAMETERS",
    "ENV_SINK_SPECS",
    "GcpDeploySpec",
    "GcpMemoryEntry",
    "GcpModelSelection",
    "GcpSecretReference",
    "RUNTIME_MODULE",
    "derive_deploy_spec",
]
