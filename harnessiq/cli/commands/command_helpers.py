"""Helper functions for the platform-first generic CLI command surface."""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from harnessiq.agents import AgentRuntimeConfig
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

_UNSET = object()


@dataclass(frozen=True, slots=True)
class _ResolvedRunRequest:
    model_factory: str | None
    model: str | None
    model_profile: str | None
    sink_specs: tuple[str, ...]
    max_cycles: int | None
    adapter_arguments: dict[str, Any]


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
    seed_cli_environment(context.repo_root)
    model = resolve_agent_model(
        model_factory=run_request.model_factory,
        model_spec=run_request.model,
        profile_name=run_request.model_profile,
    )
    runtime_config = _build_runtime_config(
        run_request.sink_specs,
        approval_policy=getattr(args, "approval_policy", None),
        allowed_tools=getattr(args, "allowed_tools", ()),
    )
    payload = _base_payload(context)
    payload["resume"] = {
        "adapter_arguments": dict(run_request.adapter_arguments),
        "max_cycles": run_request.max_cycles,
        "sink_specs": list(run_request.sink_specs),
    }
    if run_request.model_factory is not None:
        payload["resume"]["model_factory"] = run_request.model_factory
    if run_request.model is not None:
        payload["resume"]["model"] = run_request.model
    if run_request.model_profile is not None:
        payload["resume"]["profile"] = run_request.model_profile
    if source_snapshot is not None:
        payload["resume"]["source_recorded_at"] = source_snapshot.recorded_at
        payload["resume"]["source_run_number"] = source_snapshot.run_number
    payload.update(
        adapter.run(
            args=args,
            context=context,
            model=model,
            runtime_config=runtime_config,
        )
    )
    emit_json(payload)
    return 0


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
    if memory_root is None and memory_path is None:
        raise ValueError("Either memory_root or memory_path must be provided.")
    if memory_root is not None and memory_path is not None:
        raise ValueError("Only one of memory_root or memory_path may be provided.")

    if memory_root is not None:
        memory_root_path = Path(memory_root).expanduser()
        resolved_memory_path = resolve_memory_path(agent_name, memory_root_path)
        repo_root = resolve_repo_root(memory_root_path)
    else:
        resolved_memory_path = Path(memory_path).expanduser()
        repo_root = resolve_repo_root(resolved_memory_path)

    seed_profile = HarnessProfile(
        manifest_id=manifest.manifest_id,
        agent_name=agent_name,
    )
    preliminary_context = HarnessAdapterContext(
        manifest=manifest,
        agent_name=agent_name,
        memory_path=resolved_memory_path,
        repo_root=repo_root,
        profile=seed_profile,
        runtime_parameters={},
        custom_parameters={},
        bound_credentials={},
    )
    adapter.prepare(preliminary_context)
    native_runtime, native_custom = adapter.load_native_parameters(preliminary_context)
    profile_store = HarnessProfileStore(resolved_memory_path)
    if profile_store.profile_path.exists():
        profile = profile_store.load(manifest_id=manifest.manifest_id, agent_name=agent_name)
    else:
        profile = HarnessProfile(
            manifest_id=manifest.manifest_id,
            agent_name=agent_name,
            runtime_parameters=native_runtime,
            custom_parameters=native_custom,
        )

    next_runtime = dict(base_runtime_parameters if base_runtime_parameters is not None else profile.runtime_parameters)
    if incoming_runtime:
        next_runtime.update(incoming_runtime)
    next_custom = dict(base_custom_parameters if base_custom_parameters is not None else profile.custom_parameters)
    if incoming_custom:
        next_custom.update(incoming_custom)

    profile = HarnessProfile(
        manifest_id=manifest.manifest_id,
        agent_name=agent_name,
        runtime_parameters=next_runtime,
        custom_parameters=next_custom,
        last_run=profile.last_run,
        run_history=profile.run_history,
    )
    if persist_profile:
        _persist_profile(profile=profile, memory_path=resolved_memory_path, repo_root=repo_root)
    runtime_parameters = manifest.resolve_runtime_parameters(profile.runtime_parameters)
    custom_parameters = manifest.resolve_custom_parameters(profile.custom_parameters)
    context = HarnessAdapterContext(
        manifest=manifest,
        agent_name=agent_name,
        memory_path=resolved_memory_path,
        repo_root=repo_root,
        profile=profile,
        runtime_parameters=runtime_parameters,
        custom_parameters=custom_parameters,
        bound_credentials=_resolve_bound_credentials(manifest, agent_name, repo_root),
    )
    adapter.synchronize_profile(context)
    return context


def _persist_profile(*, profile: HarnessProfile, memory_path: Path, repo_root: Path) -> HarnessProfile:
    HarnessProfileStore(memory_path).save(profile)
    index_roots = {repo_root.resolve(), resolve_repo_root(Path.cwd()).resolve()}
    for index_root in index_roots:
        HarnessProfileIndexStore(index_root).upsert(
            manifest_id=profile.manifest_id,
            agent_name=profile.agent_name,
            memory_path=memory_path,
            updated_at=(profile.last_run.recorded_at if profile.last_run is not None else None),
        )
    return profile


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
    store = CredentialsConfigStore(repo_root=repo_root)
    binding_name = _binding_name(manifest, agent_name)
    try:
        binding = store.load().binding_for(binding_name)
    except AgentCredentialsNotConfiguredError:
        return {}
    resolved = store.resolve_binding(binding)
    resolved_by_family = _group_resolved_values(resolved.as_dict())
    credential_objects: dict[str, object] = {}
    for family, values in resolved_by_family.items():
        credential_objects[family] = get_provider_credential_spec(family).build_credentials(values)
    return credential_objects


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
    normalized_run_number = _normalize_resume_run_number(requested_run_number)
    if normalized_run_number is not None and not resume_requested:
        raise ValueError("--run requires --resume when used with 'run <harness>'.")
    snapshot = resume_snapshot if resume_snapshot is not None else profile.last_run
    if resume_requested and snapshot is None:
        raise ValueError(
            f"Harness profile '{profile.agent_name}' does not have a previously persisted run payload to resume."
        )

    if resume_requested:
        model_factory, model, model_profile = _merge_model_selection(
            snapshot=snapshot,
            override_model_factory=getattr(args, "model_factory", None),
            override_model=getattr(args, "model", None),
            override_model_profile=getattr(args, "model_profile", None),
        )
        sink_specs = tuple(args.sink) if args.sink else snapshot.sink_specs
        max_cycles = args.max_cycles if args.max_cycles is not None else snapshot.max_cycles
        adapter_arguments = dict(snapshot.adapter_arguments)
        for argument_name in adapter_argument_names:
            explicit_value = _explicit_run_argument_value(args, argument_name, run_argument_defaults)
            if explicit_value is not _UNSET:
                adapter_arguments[argument_name] = explicit_value
        adapter_arguments.update(run_argument_overrides)
        return _ResolvedRunRequest(
            model_factory=model_factory,
            model=model,
            model_profile=model_profile,
            sink_specs=tuple(sink_specs),
            max_cycles=max_cycles,
            adapter_arguments=adapter_arguments,
        )

    model_factory, model, model_profile = _collect_model_selection(
        model_factory=getattr(args, "model_factory", None),
        model=getattr(args, "model", None),
        model_profile=getattr(args, "model_profile", None),
        required=True,
    )
    adapter_arguments = {argument_name: getattr(args, argument_name) for argument_name in adapter_argument_names}
    adapter_arguments.update(run_argument_overrides)
    return _ResolvedRunRequest(
        model_factory=model_factory,
        model=model,
        model_profile=model_profile,
        sink_specs=tuple(args.sink),
        max_cycles=args.max_cycles,
        adapter_arguments=adapter_arguments,
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
    if snapshot is None:
        raise ValueError("The selected profile has no persisted run payload to resume.")
    resolved_model_factory, resolved_model, resolved_model_profile = _merge_model_selection(
        snapshot=snapshot,
        override_model_factory=model_factory,
        override_model=model,
        override_model_profile=model_profile,
    )
    resolved_sink_specs = tuple(sink_specs) if sink_specs else snapshot.sink_specs
    resolved_max_cycles = max_cycles if max_cycles is not None else snapshot.max_cycles
    adapter_arguments = dict(snapshot.adapter_arguments)
    adapter_arguments.update(run_argument_overrides)
    return _ResolvedRunRequest(
        model_factory=resolved_model_factory,
        model=resolved_model,
        model_profile=resolved_model_profile,
        sink_specs=tuple(resolved_sink_specs),
        max_cycles=resolved_max_cycles,
        adapter_arguments=adapter_arguments,
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


def _explicit_run_argument_value(
    args: argparse.Namespace,
    name: str,
    run_argument_defaults: dict[str, Any],
) -> Any:
    if not hasattr(args, name):
        return _UNSET
    value = getattr(args, name)
    default = run_argument_defaults.get(name)
    if value == default:
        return _UNSET
    return value


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


def _collect_model_selection(
    *,
    model_factory: str | None,
    model: str | None,
    model_profile: str | None,
    required: bool,
) -> tuple[str | None, str | None, str | None]:
    normalized_model_factory = _normalize_optional_string(model_factory)
    normalized_model = _normalize_optional_string(model)
    normalized_model_profile = _normalize_optional_string(model_profile)
    selected_count = sum(
        1
        for value in (
            normalized_model_factory,
            normalized_model,
            normalized_model_profile,
        )
        if value is not None
    )
    if required and selected_count != 1:
        raise ValueError("Exactly one of --model, --profile, or --model-factory must be provided.")
    if not required and selected_count > 1:
        raise ValueError("Exactly one of --model, --profile, or --model-factory may be provided.")
    return normalized_model_factory, normalized_model, normalized_model_profile


def _merge_model_selection(
    *,
    snapshot: HarnessRunSnapshot,
    override_model_factory: str | None,
    override_model: str | None,
    override_model_profile: str | None,
) -> tuple[str | None, str | None, str | None]:
    model_factory, model, model_profile = _collect_model_selection(
        model_factory=override_model_factory,
        model=override_model,
        model_profile=override_model_profile,
        required=False,
    )
    if any(value is not None for value in (model_factory, model, model_profile)):
        return model_factory, model, model_profile
    return snapshot.model_factory, snapshot.model, snapshot.model_profile


def _normalize_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


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


def _build_runtime_config(
    sink_specs: tuple[str, ...] | list[str],
    *,
    approval_policy: str | None = None,
    allowed_tools: tuple[str, ...] | list[str] = (),
) -> AgentRuntimeConfig:
    connections = ConnectionsConfigStore().load().enabled_connections()
    return AgentRuntimeConfig(
        approval_policy=approval_policy or DEFAULT_APPROVAL_POLICY,
        allowed_tools=parse_allowed_tool_values(allowed_tools),
        output_sinks=build_output_sinks(connections=connections, sink_specs=list(sink_specs)),
    )


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
