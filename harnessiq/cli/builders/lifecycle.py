"""Shared lifecycle builders for manifest-backed CLI flows."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from harnessiq.cli.adapters.base import HarnessCliAdapter
from harnessiq.cli.adapters.context import HarnessAdapterContext
from harnessiq.cli.common import resolve_memory_path, resolve_repo_root
from harnessiq.config import (
    AgentCredentialBinding,
    AgentCredentialsNotConfiguredError,
    CredentialEnvReference,
    CredentialsConfigStore,
    HarnessProfile,
    HarnessProfileIndexStore,
    HarnessProfileStore,
    get_provider_credential_spec,
)
from harnessiq.shared.dtos import HarnessParameterBundleDTO
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
        native_parameters = adapter.load_native_parameters(preliminary_context)
        if isinstance(native_parameters, tuple):
            native_runtime, native_custom = native_parameters
            native_parameters = HarnessParameterBundleDTO(
                runtime_parameters=dict(native_runtime),
                custom_parameters=dict(native_custom),
            )
        profile = self._load_or_seed_profile(
            manifest=manifest,
            agent_name=agent_name,
            memory_path=resolved_memory_path,
            native_runtime=dict(native_parameters.runtime_parameters),
            native_custom=dict(native_parameters.custom_parameters),
        )
        merged_profile = self._merge_profile_parameters(
            profile=profile,
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
            bound_credentials=self.resolve_bound_credentials(
                manifest=manifest,
                agent_name=agent_name,
                repo_root=repo_root,
            ),
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

    def build_inspection_payload(
        self,
        *,
        manifest: HarnessManifest,
    ) -> dict[str, Any]:
        return {
            "harness": manifest.manifest_id,
            "display_name": manifest.display_name,
            "import_path": manifest.import_path,
            "cli_command": manifest.cli_command,
            "cli_adapter_path": manifest.cli_adapter_path,
            "default_memory_root": manifest.resolved_default_memory_root,
            "runtime_parameters": [self._render_parameter_spec(spec) for spec in manifest.runtime_parameters],
            "custom_parameters": [self._render_parameter_spec(spec) for spec in manifest.custom_parameters],
            "runtime_parameters_open_ended": manifest.runtime_parameters_open_ended,
            "custom_parameters_open_ended": manifest.custom_parameters_open_ended,
            "memory_files": [
                {
                    "key": entry.key,
                    "relative_path": entry.relative_path,
                    "description": entry.description,
                    "kind": entry.kind,
                    "format": entry.format,
                }
                for entry in manifest.memory_files
            ],
            "provider_families": list(manifest.provider_families),
            "provider_credential_fields": self._build_provider_credential_fields(manifest),
            "output_schema": manifest.output_schema,
        }

    def bind_credentials(
        self,
        *,
        manifest: HarnessManifest,
        agent_name: str,
        memory_root: str | Path,
        assignments: list[str],
        description: str | None,
    ) -> dict[str, Any]:
        store, binding_name = self._resolve_credentials_store(
            manifest=manifest,
            agent_name=agent_name,
            memory_root=memory_root,
        )
        existing_references = self._load_existing_binding_references(store, binding_name)
        updated_references = dict(existing_references)
        for assignment in assignments:
            field_name, env_var = self._parse_reference_assignment(assignment)
            updated_references[field_name] = env_var
        self._validate_binding_references(manifest, updated_references)
        binding = AgentCredentialBinding(
            agent_name=binding_name,
            references=tuple(
                CredentialEnvReference(field_name=field_name, env_var=env_var)
                for field_name, env_var in sorted(updated_references.items())
            ),
            description=description,
        )
        config_path = store.upsert(binding)
        return {
            "agent": agent_name,
            "binding_name": binding_name,
            "config_path": str(config_path),
            "families": self._group_reference_mapping(updated_references),
            "harness": manifest.manifest_id,
            "status": "bound",
        }

    def show_credentials(
        self,
        *,
        manifest: HarnessManifest,
        agent_name: str,
        memory_root: str | Path,
    ) -> dict[str, Any]:
        store, binding_name = self._resolve_credentials_store(
            manifest=manifest,
            agent_name=agent_name,
            memory_root=memory_root,
        )
        try:
            binding = store.load().binding_for(binding_name)
        except AgentCredentialsNotConfiguredError:
            return {
                "agent": agent_name,
                "binding_name": binding_name,
                "bound": False,
                "harness": manifest.manifest_id,
                "provider_families": list(manifest.provider_families),
            }
        mapping = {reference.field_name: reference.env_var for reference in binding.references}
        return {
            "agent": agent_name,
            "binding_name": binding_name,
            "bound": True,
            "config_path": str(store.config_path),
            "description": binding.description,
            "families": self._group_reference_mapping(mapping),
            "harness": manifest.manifest_id,
        }

    def test_credentials(
        self,
        *,
        manifest: HarnessManifest,
        agent_name: str,
        memory_root: str | Path,
    ) -> dict[str, Any]:
        store, binding_name = self._resolve_credentials_store(
            manifest=manifest,
            agent_name=agent_name,
            memory_root=memory_root,
        )
        binding = store.load().binding_for(binding_name)
        resolved = store.resolve_binding(binding)
        resolved_by_family = self._group_resolved_values(resolved.as_dict())
        payload_by_family: dict[str, Any] = {}
        for family, values in resolved_by_family.items():
            spec = get_provider_credential_spec(family)
            credential_object = spec.build_credentials(values)
            if hasattr(credential_object, "as_redacted_dict"):
                payload_by_family[family] = credential_object.as_redacted_dict()  # type: ignore[assignment]
            else:
                payload_by_family[family] = spec.redact_values(values)
        return {
            "agent": agent_name,
            "binding_name": binding_name,
            "env_path": str(resolved.env_path),
            "families": payload_by_family,
            "harness": manifest.manifest_id,
            "status": "resolved",
        }

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
            manifest_id=profile.manifest_id,
            agent_name=profile.agent_name,
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

    def _resolve_credentials_store(
        self,
        *,
        manifest: HarnessManifest,
        agent_name: str,
        memory_root: str | Path,
    ) -> tuple[CredentialsConfigStore, str]:
        repo_root = resolve_repo_root(Path(memory_root).expanduser())
        return (
            CredentialsConfigStore(repo_root=repo_root),
            self._binding_name(manifest=manifest, agent_name=agent_name),
        )

    def _build_provider_credential_fields(
        self,
        manifest: HarnessManifest,
    ) -> dict[str, list[dict[str, str]]]:
        credential_fields: dict[str, list[dict[str, str]]] = {}
        for family in manifest.provider_families:
            try:
                spec = get_provider_credential_spec(family)
            except KeyError:
                credential_fields[family] = []
                continue
            credential_fields[family] = [
                {"name": field.name, "description": field.description}
                for field in spec.fields
            ]
        return credential_fields

    def _validate_binding_references(
        self,
        manifest: HarnessManifest,
        references: dict[str, str],
    ) -> None:
        grouped: dict[str, dict[str, str]] = defaultdict(dict)
        provider_families = set(manifest.provider_families)
        for field_name, env_var in references.items():
            family, separator, credential_field = field_name.partition(".")
            if not separator:
                raise ValueError(
                    f"Credential field '{field_name}' must use FAMILY.FIELD notation, for example exa.api_key."
                )
            normalized_family = family.strip().lower()
            if normalized_family not in provider_families:
                raise ValueError(
                    f"Harness '{manifest.manifest_id}' does not declare provider family '{normalized_family}'."
                )
            grouped[normalized_family][credential_field] = env_var
        for family, values in grouped.items():
            get_provider_credential_spec(family).validate_fields(values)

    def _load_existing_binding_references(
        self,
        store: CredentialsConfigStore,
        binding_name: str,
    ) -> dict[str, str]:
        try:
            binding = store.load().binding_for(binding_name)
        except AgentCredentialsNotConfiguredError:
            return {}
        return {reference.field_name: reference.env_var for reference in binding.references}

    def _parse_reference_assignment(self, assignment: str) -> tuple[str, str]:
        field_name, env_var = assignment.split("=", 1) if "=" in assignment else (assignment, "")
        normalized_field_name = field_name.strip()
        normalized_env_var = env_var.strip()
        if not normalized_field_name or not normalized_env_var:
            raise ValueError(
                f"Credential bindings must use FAMILY.FIELD=ENV_VAR syntax. Received '{assignment}'."
            )
        return normalized_field_name, normalized_env_var

    def _group_reference_mapping(self, mapping: dict[str, str]) -> dict[str, dict[str, str]]:
        grouped: dict[str, dict[str, str]] = defaultdict(dict)
        for field_name, env_var in mapping.items():
            family, _, credential_field = field_name.partition(".")
            grouped[family][credential_field] = env_var
        return {family: dict(values) for family, values in sorted(grouped.items())}

    def _group_resolved_values(self, mapping: dict[str, str]) -> dict[str, dict[str, str]]:
        grouped: dict[str, dict[str, str]] = {}
        for field_name, value in mapping.items():
            family, separator, credential_field = field_name.partition(".")
            if not separator:
                continue
            family_values = grouped.setdefault(family, {})
            family_values[credential_field] = value
        return {family: dict(values) for family, values in grouped.items()}

    def _render_parameter_spec(self, spec) -> dict[str, Any]:
        return {
            "key": spec.key,
            "type": spec.value_type,
            "description": spec.description,
            "nullable": spec.nullable,
            "default": spec.default,
            "choices": list(spec.choices),
        }


__all__ = ["HarnessCliLifecycleBuilder"]
