"""Helper functions for the platform-first generic CLI command surface."""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from harnessiq.agents import AgentRuntimeConfig
from harnessiq.cli.builders import HarnessCliLifecycleBuilder
from harnessiq.cli.runners import HarnessCliLifecycleRunner, ResolvedRunRequest
from harnessiq.cli._langsmith import seed_cli_environment
from harnessiq.cli.adapters import HarnessAdapterContext
from harnessiq.cli.common import (
    emit_json,
    load_factory,
    parse_allowed_tool_values,
    parse_manifest_parameter_assignments,
    resolve_agent_model,
    resolve_memory_path,
    resolve_repo_root,
)
from harnessiq.cli.interactive import select_index
from harnessiq.config import (
    AgentCredentialsNotConfiguredError,
    CredentialsConfigStore,
    HarnessProfile,
    HarnessProfileIndexStore,
    HarnessProfileStore,
    HarnessRunSnapshot,
    get_provider_credential_spec,
)
from harnessiq.shared.harness_manifest import HarnessManifest
from harnessiq.shared.hooks import DEFAULT_APPROVAL_POLICY
from harnessiq.shared.harness_manifests import get_harness_manifest, list_harness_manifests
from harnessiq.utils import ConnectionsConfigStore, build_output_sinks

_ResolvedRunRequest = ResolvedRunRequest


@dataclass(frozen=True, slots=True)
class _ResumeCandidate:
    manifest: HarnessManifest
    agent_name: str
    memory_path: Path
    profile: HarnessProfile

    @property
    def label(self) -> str:
        recorded_at = self.profile.last_run.recorded_at if self.profile.last_run is not None else "unknown"
        run_number = self.profile.last_run.run_number if self.profile.last_run is not None else "?"
        return (
            f"{self.manifest.display_name} | {self.memory_path.as_posix()} | "
            f"last run #{run_number} at {recorded_at} ({len(self.profile.run_history)} stored)"
        )


def _execute_run(
    *,
    adapter,
    args: argparse.Namespace,
    context: HarnessAdapterContext,
    run_request: _ResolvedRunRequest,
    source_snapshot: HarnessRunSnapshot | None = None,
) -> int:
    return HarnessCliLifecycleRunner().execute_run(
        adapter=adapter,
        args=args,
        context=context,
        run_request=run_request,
        base_payload=_base_payload(context),
        source_snapshot=source_snapshot,
    )


def _build_context(
    *,
    manifest: HarnessManifest,
    adapter,
    agent_name: str,
    incoming_runtime: dict[str, Any],
    incoming_custom: dict[str, Any],
    persist_profile: bool,
    memory_root: str | None = None,
    memory_path: Path | str | None = None,
    base_runtime_parameters: dict[str, Any] | None = None,
    base_custom_parameters: dict[str, Any] | None = None,
) -> HarnessAdapterContext:
    return HarnessCliLifecycleBuilder().build_context(
        manifest=manifest,
        adapter=adapter,
        agent_name=agent_name,
        incoming_runtime=incoming_runtime,
        incoming_custom=incoming_custom,
        persist_profile=persist_profile,
        memory_root=memory_root,
        memory_path=memory_path,
        base_runtime_parameters=base_runtime_parameters,
        base_custom_parameters=base_custom_parameters,
    )


def _persist_profile(*, profile: HarnessProfile, memory_path: Path, repo_root: Path) -> HarnessProfile:
    return HarnessCliLifecycleBuilder().persist_profile(
        profile=profile,
        memory_path=memory_path,
        repo_root=repo_root,
    )


def _persist_run_snapshot(
    context: HarnessAdapterContext,
    run_request: _ResolvedRunRequest,
) -> HarnessAdapterContext:
    profile = context.profile.append_run_snapshot(
        HarnessRunSnapshot(
            model_factory=run_request.model_factory,
            model=run_request.model,
            model_profile=run_request.model_profile,
            sink_specs=run_request.sink_specs,
            max_cycles=run_request.max_cycles,
            adapter_arguments=run_request.adapter_arguments,
            runtime_parameters=context.profile.runtime_parameters,
            custom_parameters=context.profile.custom_parameters,
        )
    )
    _persist_profile(profile=profile, memory_path=context.memory_path, repo_root=context.repo_root)
    return replace(context, profile=profile)


def _resolve_bound_credentials(
    manifest: HarnessManifest,
    agent_name: str,
    repo_root: Path,
) -> dict[str, object]:
    return HarnessCliLifecycleBuilder().resolve_bound_credentials(
        manifest=manifest,
        agent_name=agent_name,
        repo_root=repo_root,
    )


def _resolve_run_request(
    *,
    args: argparse.Namespace,
    profile: HarnessProfile,
    resume_requested: bool,
    resume_snapshot: HarnessRunSnapshot | None,
    requested_run_number: int | None,
    run_argument_defaults: dict[str, Any],
    adapter_argument_names: tuple[str, ...],
    run_argument_overrides: dict[str, Any],
) -> _ResolvedRunRequest:
    return HarnessCliLifecycleRunner().resolve_run_request(
        args=args,
        profile=profile,
        resume_requested=resume_requested,
        resume_snapshot=resume_snapshot,
        requested_run_number=requested_run_number,
        run_argument_defaults=run_argument_defaults,
        adapter_argument_names=adapter_argument_names,
        run_argument_overrides=run_argument_overrides,
    )


def _resolve_resume_request_from_snapshot(
    *,
    snapshot: HarnessRunSnapshot | None,
    model_factory: str | None,
    model: str | None,
    model_profile: str | None,
    sink_specs: list[str],
    max_cycles: int | None,
    run_argument_overrides: dict[str, Any],
) -> _ResolvedRunRequest:
    return HarnessCliLifecycleRunner().resolve_resume_request_from_snapshot(
        snapshot=snapshot,
        model_factory=model_factory,
        model=model,
        model_profile=model_profile,
        sink_specs=sink_specs,
        max_cycles=max_cycles,
        run_argument_overrides=run_argument_overrides,
    )


def _resolve_profile_resume_snapshot(
    *,
    profile: HarnessProfile,
    run_number: int | None,
) -> HarnessRunSnapshot:
    normalized_run_number = _normalize_resume_run_number(run_number)
    snapshot = profile.snapshot_for_run_number(normalized_run_number)
    if snapshot is not None:
        return snapshot
    if normalized_run_number is None:
        raise ValueError(
            f"Harness profile '{profile.agent_name}' does not have a previously persisted run payload to resume."
        )
    available_runs = ", ".join(str(item.run_number) for item in profile.run_history)
    raise ValueError(
        f"Harness profile '{profile.agent_name}' does not have persisted run #{normalized_run_number}. "
        f"Available runs: {available_runs or 'none'}."
    )


def _normalize_resume_run_number(run_number: int | None) -> int | None:
    if run_number is None:
        return None
    if run_number < 1:
        raise ValueError("--run must be greater than or equal to 1.")
    return run_number


def _clone_args_with_run_request(
    args: argparse.Namespace,
    run_request: _ResolvedRunRequest,
) -> argparse.Namespace:
    payload = vars(args).copy()
    payload["model_factory"] = run_request.model_factory
    payload["model"] = run_request.model
    payload["model_profile"] = run_request.model_profile
    payload["sink"] = list(run_request.sink_specs)
    payload["max_cycles"] = run_request.max_cycles
    payload.update(run_request.adapter_arguments)
    return argparse.Namespace(**payload)


def _resolve_resume_agent_name(args: argparse.Namespace) -> str:
    positional = (args.agent_name or "").strip()
    flag_value = (args.agent_flag or "").strip()
    if positional and flag_value and positional != flag_value:
        raise ValueError(
            f"Resume target conflict: positional agent '{positional}' does not match --agent '{flag_value}'."
        )
    resolved = flag_value or positional
    if not resolved:
        raise ValueError("Resume requires an agent name. Pass it positionally or with --agent.")
    return resolved


def _resolve_resume_manifest(query: str | None) -> HarnessManifest | None:
    if query is None or not query.strip():
        return None
    return get_harness_manifest(query)


def _discover_resume_candidates(
    *,
    repo_root: Path,
    agent_name: str,
    manifest: HarnessManifest | None,
) -> list[_ResumeCandidate]:
    manifests = (manifest,) if manifest is not None else list_harness_manifests()
    seen_paths: set[tuple[str, str]] = set()
    candidates: list[_ResumeCandidate] = []

    index_store = HarnessProfileIndexStore(repo_root)
    indexed_records = index_store.list(
        agent_name=agent_name,
        manifest_id=(manifest.manifest_id if manifest is not None else None),
    )
    for record in indexed_records:
        resolved_manifest = get_harness_manifest(record.manifest_id)
        candidate = _load_resume_candidate(
            manifest=resolved_manifest,
            agent_name=record.agent_name,
            memory_path=record.memory_path,
        )
        if candidate is None:
            continue
        key = (candidate.manifest.manifest_id, candidate.memory_path.resolve().as_posix())
        if key in seen_paths:
            continue
        seen_paths.add(key)
        candidates.append(candidate)

    for candidate_manifest in manifests:
        default_root = _resolve_default_memory_root(repo_root, candidate_manifest)
        default_memory_path = resolve_memory_path(agent_name, default_root)
        candidate = _load_resume_candidate(
            manifest=candidate_manifest,
            agent_name=agent_name,
            memory_path=default_memory_path,
        )
        if candidate is None:
            continue
        key = (candidate.manifest.manifest_id, candidate.memory_path.resolve().as_posix())
        if key in seen_paths:
            continue
        seen_paths.add(key)
        candidates.append(candidate)

    candidates.sort(
        key=lambda item: (
            item.profile.last_run.recorded_at if item.profile.last_run is not None else "",
            item.manifest.manifest_id,
            item.memory_path.as_posix(),
        ),
        reverse=True,
    )
    return candidates


def _load_resume_candidate(
    *,
    manifest: HarnessManifest,
    agent_name: str,
    memory_path: Path,
) -> _ResumeCandidate | None:
    profile_store = HarnessProfileStore(memory_path)
    if not profile_store.profile_path.exists():
        return None
    try:
        profile = profile_store.load(manifest_id=manifest.manifest_id, agent_name=agent_name)
    except ValueError:
        return None
    if not profile.run_history:
        return None
    return _ResumeCandidate(
        manifest=manifest,
        agent_name=agent_name,
        memory_path=Path(memory_path),
        profile=profile,
    )


def _select_resume_candidate(
    *,
    agent_name: str,
    candidates: list[_ResumeCandidate],
) -> _ResumeCandidate:
    if len(candidates) == 1:
        return candidates[0]
    selected_index = select_index(
        f"Multiple resumable profiles match '{agent_name}'. Select one:",
        [candidate.label for candidate in candidates],
    )
    return candidates[selected_index]


def _resolve_default_memory_root(repo_root: Path, manifest: HarnessManifest) -> Path:
    default_root = Path(manifest.resolved_default_memory_root).expanduser()
    if default_root.is_absolute():
        return default_root
    return repo_root / default_root


def _parse_resume_manifest_parameters(
    assignments: list[str],
    *,
    manifest: HarnessManifest,
    scope: str,
) -> dict[str, Any]:
    if not assignments:
        return {}
    return parse_manifest_parameter_assignments(assignments, manifest=manifest, scope=scope)


def _load_existing_binding_references(
    store: CredentialsConfigStore,
    binding_name: str,
) -> dict[str, str]:
    try:
        binding = store.load().binding_for(binding_name)
    except AgentCredentialsNotConfiguredError:
        return {}
    return {reference.field_name: reference.env_var for reference in binding.references}


def _validate_binding_references(
    manifest: HarnessManifest,
    references: dict[str, str],
) -> None:
    grouped: dict[str, dict[str, str]] = defaultdict(dict)
    for field_name, env_var in references.items():
        family, separator, credential_field = field_name.partition(".")
        if not separator:
            raise ValueError(
                f"Credential field '{field_name}' must use FAMILY.FIELD notation, for example exa.api_key."
            )
        normalized_family = family.strip().lower()
        if normalized_family not in set(manifest.provider_families):
            raise ValueError(
                f"Harness '{manifest.manifest_id}' does not declare provider family '{normalized_family}'."
            )
        grouped[normalized_family][credential_field] = env_var
    for family, values in grouped.items():
        get_provider_credential_spec(family).validate_fields(values)


def _parse_reference_assignment(assignment: str) -> tuple[str, str]:
    field_name, env_var = assignment.split("=", 1) if "=" in assignment else (assignment, "")
    normalized_field_name = field_name.strip()
    normalized_env_var = env_var.strip()
    if not normalized_field_name or not normalized_env_var:
        raise ValueError(
            f"Credential bindings must use FAMILY.FIELD=ENV_VAR syntax. Received '{assignment}'."
        )
    return normalized_field_name, normalized_env_var


def _group_reference_mapping(mapping: dict[str, str]) -> dict[str, dict[str, str]]:
    grouped: dict[str, dict[str, str]] = defaultdict(dict)
    for field_name, env_var in mapping.items():
        family, _, credential_field = field_name.partition(".")
        grouped[family][credential_field] = env_var
    return {family: dict(values) for family, values in sorted(grouped.items())}


def _group_resolved_values(mapping: dict[str, str]) -> dict[str, dict[str, str]]:
    grouped: dict[str, dict[str, str]] = defaultdict(dict)
    for field_name, value in mapping.items():
        family, separator, credential_field = field_name.partition(".")
        if not separator:
            continue
        grouped[family][credential_field] = value
    return {family: dict(values) for family, values in grouped.items()}


def _binding_name(manifest: HarnessManifest, agent_name: str) -> str:
    return HarnessProfile(
        manifest_id=manifest.manifest_id,
        agent_name=agent_name,
    ).credential_binding_name


def _build_adapter(manifest: HarnessManifest):
    if not manifest.cli_adapter_path:
        raise ValueError(f"Harness '{manifest.manifest_id}' does not declare a CLI adapter path.")
    adapter_factory = load_factory(manifest.cli_adapter_path)
    return adapter_factory()


def _base_payload(context: HarnessAdapterContext) -> dict[str, Any]:
    binding_name = _binding_name(context.manifest, context.agent_name)
    return {
        "agent": context.agent_name,
        "bound_credential_families": sorted(context.bound_credentials),
        "credential_binding_name": binding_name,
        "harness": context.manifest.manifest_id,
        "memory_path": str(context.memory_path.resolve()),
        "profile": {
            "config_path": str((context.memory_path / ".harnessiq-profile.json").resolve()),
            "custom_parameters": dict(context.profile.custom_parameters),
            "effective_custom_parameters": dict(context.custom_parameters),
            "effective_runtime_parameters": dict(context.runtime_parameters),
            "last_run": (
                context.profile.last_run.as_dict()
                if context.profile.last_run is not None
                else None
            ),
            "run_count": len(context.profile.run_history),
            "run_history": [snapshot.summary for snapshot in context.profile.run_history],
            "runtime_parameters": dict(context.profile.runtime_parameters),
        },
    }


def _render_parameter_spec(spec) -> dict[str, Any]:
    return {
        "key": spec.key,
        "type": spec.value_type,
        "description": spec.description,
        "nullable": spec.nullable,
        "default": spec.default,
        "choices": list(spec.choices),
    }


__all__ = [
    "_ResumeCandidate",
    "_ResolvedRunRequest",
    "_base_payload",
    "_binding_name",
    "_build_adapter",
    "_build_context",
    "_clone_args_with_run_request",
    "_discover_resume_candidates",
    "_execute_run",
    "_group_reference_mapping",
    "_group_resolved_values",
    "_load_existing_binding_references",
    "_parse_reference_assignment",
    "_parse_resume_manifest_parameters",
    "_persist_run_snapshot",
    "_render_parameter_spec",
    "_resolve_profile_resume_snapshot",
    "_resolve_resume_agent_name",
    "_resolve_resume_manifest",
    "_resolve_resume_request_from_snapshot",
    "_resolve_run_request",
    "_select_resume_candidate",
    "_validate_binding_references",
]
