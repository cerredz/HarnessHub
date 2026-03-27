"""Shared lifecycle builders for manifest-backed CLI flows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from harnessiq.cli.adapters.base import HarnessCliAdapter
from harnessiq.cli.adapters.context import HarnessAdapterContext
from harnessiq.cli.common import resolve_memory_path, resolve_repo_root
from harnessiq.config import (
    AgentCredentialsNotConfiguredError,
    CredentialsConfigStore,
    HarnessProfile,
    HarnessProfileIndexStore,
    HarnessProfileStore,
    get_provider_credential_spec,
)
from harnessiq.shared.harness_manifest import HarnessManifest


class HarnessCliLifecycleBuilder:
    """Build adapter contexts and persisted profile state for CLI lifecycle actions."""

    def __init__(self, *, cwd: Path | str | None = None) -> None:
        self._cwd = Path.cwd() if cwd is None else Path(cwd)

    def build_context(
        self,
        *,
        manifest: HarnessManifest,
        adapter: HarnessCliAdapter,
        agent_name: str,
        incoming_runtime: dict[str, Any],
        incoming_custom: dict[str, Any],
        persist_profile: bool,
        memory_root: str | None = None,
        memory_path: Path | str | None = None,
        base_runtime_parameters: dict[str, Any] | None = None,
        base_custom_parameters: dict[str, Any] | None = None,
    ) -> HarnessAdapterContext:
        resolved_memory_path, repo_root = self._resolve_memory_context(
            agent_name=agent_name,
            memory_root=memory_root,
            memory_path=memory_path,
        )
        preliminary_context = self._build_preliminary_context(
            manifest=manifest,
            agent_name=agent_name,
            memory_path=resolved_memory_path,
            repo_root=repo_root,
        )
        adapter.prepare(preliminary_context)
        native_runtime, native_custom = adapter.load_native_parameters(preliminary_context)
        profile = self._load_or_seed_profile(
            manifest=manifest,
            agent_name=agent_name,
            memory_path=resolved_memory_path,
            native_runtime=native_runtime,
            native_custom=native_custom,
        )
        merged_profile = self._merge_profile_parameters(
            profile=profile,
            manifest=manifest,
            agent_name=agent_name,
            incoming_runtime=incoming_runtime,
            incoming_custom=incoming_custom,
            base_runtime_parameters=base_runtime_parameters,
            base_custom_parameters=base_custom_parameters,
        )
        if persist_profile:
            self.persist_profile(profile=merged_profile, memory_path=resolved_memory_path, repo_root=repo_root)
        context = HarnessAdapterContext(
            manifest=manifest,
            agent_name=agent_name,
            memory_path=resolved_memory_path,
            repo_root=repo_root,
            profile=merged_profile,
            runtime_parameters=manifest.resolve_runtime_parameters(merged_profile.runtime_parameters),
            custom_parameters=manifest.resolve_custom_parameters(merged_profile.custom_parameters),
            bound_credentials=self.resolve_bound_credentials(manifest=manifest, agent_name=agent_name, repo_root=repo_root),
        )
        adapter.synchronize_profile(context)
        return context

    def persist_profile(
        self,
        *,
        profile: HarnessProfile,
        memory_path: Path,
        repo_root: Path,
    ) -> HarnessProfile:
        HarnessProfileStore(memory_path).save(profile)
        index_roots = {repo_root.resolve(), resolve_repo_root(self._cwd).resolve()}
        for index_root in index_roots:
            HarnessProfileIndexStore(index_root).upsert(
                manifest_id=profile.manifest_id,
                agent_name=profile.agent_name,
                memory_path=memory_path,
                updated_at=(profile.last_run.recorded_at if profile.last_run is not None else None),
            )
        return profile

    def resolve_bound_credentials(
        self,
        *,
        manifest: HarnessManifest,
        agent_name: str,
        repo_root: Path,
    ) -> dict[str, object]:
        store = CredentialsConfigStore(repo_root=repo_root)
        binding_name = self._binding_name(manifest=manifest, agent_name=agent_name)
        try:
            binding = store.load().binding_for(binding_name)
        except AgentCredentialsNotConfiguredError:
            return {}
        resolved = store.resolve_binding(binding)
        resolved_by_family = self._group_resolved_values(resolved.as_dict())
        credential_objects: dict[str, object] = {}
        for family, values in resolved_by_family.items():
            credential_objects[family] = get_provider_credential_spec(family).build_credentials(values)
        return credential_objects

    def _resolve_memory_context(
        self,
        *,
        agent_name: str,
        memory_root: str | None,
        memory_path: Path | str | None,
    ) -> tuple[Path, Path]:
        if memory_root is None and memory_path is None:
            raise ValueError("Either memory_root or memory_path must be provided.")
        if memory_root is not None and memory_path is not None:
            raise ValueError("Only one of memory_root or memory_path may be provided.")
        if memory_root is not None:
            memory_root_path = Path(memory_root).expanduser()
            return resolve_memory_path(agent_name, memory_root_path), resolve_repo_root(memory_root_path)
        resolved_memory_path = Path(memory_path).expanduser()
        return resolved_memory_path, resolve_repo_root(resolved_memory_path)

    def _build_preliminary_context(
        self,
        *,
        manifest: HarnessManifest,
        agent_name: str,
        memory_path: Path,
        repo_root: Path,
    ) -> HarnessAdapterContext:
        return HarnessAdapterContext(
            manifest=manifest,
            agent_name=agent_name,
            memory_path=memory_path,
            repo_root=repo_root,
            profile=HarnessProfile(
                manifest_id=manifest.manifest_id,
                agent_name=agent_name,
            ),
            runtime_parameters={},
            custom_parameters={},
            bound_credentials={},
        )

    def _load_or_seed_profile(
        self,
        *,
        manifest: HarnessManifest,
        agent_name: str,
        memory_path: Path,
        native_runtime: dict[str, Any],
        native_custom: dict[str, Any],
    ) -> HarnessProfile:
        profile_store = HarnessProfileStore(memory_path)
        if profile_store.profile_path.exists():
            return profile_store.load(manifest_id=manifest.manifest_id, agent_name=agent_name)
        return HarnessProfile(
            manifest_id=manifest.manifest_id,
            agent_name=agent_name,
            runtime_parameters=native_runtime,
            custom_parameters=native_custom,
        )

    def _merge_profile_parameters(
        self,
        *,
        profile: HarnessProfile,
        manifest: HarnessManifest,
        agent_name: str,
        incoming_runtime: dict[str, Any],
        incoming_custom: dict[str, Any],
        base_runtime_parameters: dict[str, Any] | None,
        base_custom_parameters: dict[str, Any] | None,
    ) -> HarnessProfile:
        next_runtime = dict(base_runtime_parameters if base_runtime_parameters is not None else profile.runtime_parameters)
        if incoming_runtime:
            next_runtime.update(incoming_runtime)
        next_custom = dict(base_custom_parameters if base_custom_parameters is not None else profile.custom_parameters)
        if incoming_custom:
            next_custom.update(incoming_custom)
        return HarnessProfile(
            manifest_id=manifest.manifest_id,
            agent_name=agent_name,
            runtime_parameters=next_runtime,
            custom_parameters=next_custom,
            last_run=profile.last_run,
            run_history=profile.run_history,
        )

    def _binding_name(self, *, manifest: HarnessManifest, agent_name: str) -> str:
        return HarnessProfile(
            manifest_id=manifest.manifest_id,
            agent_name=agent_name,
        ).credential_binding_name

    def _group_resolved_values(self, mapping: dict[str, str]) -> dict[str, dict[str, str]]:
        grouped: dict[str, dict[str, str]] = {}
        for field_name, value in mapping.items():
            family, separator, credential_field = field_name.partition(".")
            if not separator:
                continue
            family_values = grouped.setdefault(family, {})
            family_values[credential_field] = value
        return {family: dict(values) for family, values in grouped.items()}


__all__ = ["HarnessCliLifecycleBuilder"]
