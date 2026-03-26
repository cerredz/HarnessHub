"""Platform-first root CLI commands for harness lifecycle and credentials."""

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
    add_agent_options,
    add_manifest_parameter_options,
    add_model_selection_options,
    collect_manifest_parameter_values,
    emit_json,
    load_factory,
    parse_generic_assignments,
    parse_manifest_parameter_assignments,
    resolve_agent_model_from_args,
    resolve_memory_path,
    resolve_repo_root,
)
from harnessiq.cli.interactive import select_index
from harnessiq.config import (
    AgentCredentialBinding,
    AgentCredentialsNotConfiguredError,
    CredentialEnvReference,
    CredentialsConfigStore,
    HarnessProfile,
    HarnessProfileIndexStore,
    HarnessProfileStore,
    HarnessRunSnapshot,
    get_provider_credential_spec,
)
from harnessiq.shared.harness_manifest import HarnessManifest
from harnessiq.shared.harness_manifests import get_harness_manifest, list_harness_manifests
from harnessiq.utils import ConnectionsConfigStore, build_output_sinks

_RUN_ARGUMENT_DEFAULTS_DEST = "_run_argument_defaults"
_RUN_ADAPTER_ARGUMENT_NAMES_DEST = "_run_adapter_argument_names"
_UNSET = object()


@dataclass(frozen=True, slots=True)
class _ResolvedRunRequest:
    model_factory: str | None
    model_spec: str | None
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


def register_platform_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    prepare_parser = subparsers.add_parser("prepare", help="Prepare and persist generic config for a harness")
    prepare_parser.set_defaults(command_handler=lambda args: _print_help(prepare_parser))
    _register_manifest_subcommands(prepare_parser, command="prepare")

    show_parser = subparsers.add_parser("show", help="Show persisted platform config and harness state")
    show_parser.set_defaults(command_handler=lambda args: _print_help(show_parser))
    _register_manifest_subcommands(show_parser, command="show")

    run_parser = subparsers.add_parser("run", help="Run a harness through the platform-first CLI")
    run_parser.set_defaults(command_handler=lambda args: _print_help(run_parser))
    _register_manifest_subcommands(run_parser, command="run")

    resume_parser = subparsers.add_parser(
        "resume",
        help="Resume a previously run platform-first harness by logical agent profile name",
    )
    resume_parser.add_argument("agent_name", nargs="?", help="Logical agent profile name to resume.")
    resume_parser.add_argument("--agent", dest="agent_flag", help="Logical agent profile name to resume.")
    resume_parser.add_argument(
        "--harness",
        help="Optional harness manifest id, runtime agent name, or CLI command used to narrow resume lookup.",
    )
    resume_parser.add_argument(
        "--model-factory",
        help="Optional override for the persisted model factory import path.",
    )
    resume_parser.add_argument(
        "--run",
        dest="resume_run_number",
        type=int,
        help="Specific persisted run number to resume; defaults to the latest stored run.",
    )
    resume_parser.add_argument(
        "--sink",
        action="append",
        default=[],
        metavar="SPEC",
        help="Optional per-run output sink override using kind:value or kind:key=value,key=value.",
    )
    resume_parser.add_argument("--max-cycles", type=int, help="Optional max cycle count override.")
    resume_parser.add_argument(
        "--runtime-param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Optional runtime-parameter override applied to the selected harness profile.",
    )
    resume_parser.add_argument(
        "--custom-param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Optional custom-parameter override applied to the selected harness profile.",
    )
    resume_parser.add_argument(
        "--run-arg",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Optional override for persisted harness-specific run-only arguments.",
    )
    resume_parser.set_defaults(command_handler=_handle_resume)

    inspect_parser = subparsers.add_parser("inspect", help="Inspect one harness manifest and generated CLI surface")
    inspect_parser.set_defaults(command_handler=lambda args: _print_help(inspect_parser))
    _register_manifest_subcommands(inspect_parser, command="inspect")

    credentials_parser = subparsers.add_parser("credentials", help="Manage persisted harness credential bindings")
    credentials_parser.set_defaults(command_handler=lambda args: _print_help(credentials_parser))
    credentials_subparsers = credentials_parser.add_subparsers(dest="credentials_command")
    for action in ("bind", "show", "test"):
        action_parser = credentials_subparsers.add_parser(action, help=f"{action.title()} harness credentials")
        action_parser.set_defaults(command_handler=lambda args, parser=action_parser: _print_help(parser))
        _register_manifest_subcommands(action_parser, command=f"credentials_{action}")


def _register_manifest_subcommands(
    root_parser: argparse.ArgumentParser,
    *,
    command: str,
) -> None:
    manifest_subparsers = root_parser.add_subparsers(dest=f"{command}_harness")
    for manifest in list_harness_manifests():
        aliases = []
        if manifest.cli_command is not None and manifest.cli_command != manifest.manifest_id:
            aliases.append(manifest.cli_command)
        parser = manifest_subparsers.add_parser(
            manifest.manifest_id,
            aliases=aliases,
            help=f"{command.replace('credentials_', '')} {manifest.display_name}",
        )
        if command in {"prepare", "show", "run", "credentials_bind", "credentials_show", "credentials_test"}:
            add_agent_options(
                parser,
                agent_help=f"Logical {manifest.display_name} profile name used to resolve the memory folder.",
                memory_root_default=manifest.resolved_default_memory_root,
                memory_root_help=f"Root directory that holds per-profile {manifest.display_name} memory folders.",
            )
        if command == "prepare":
            add_manifest_parameter_options(parser, manifest=manifest, scope="runtime")
            add_manifest_parameter_options(parser, manifest=manifest, scope="custom")
            parser.set_defaults(command_handler=_handle_prepare, manifest_id=manifest.manifest_id)
        elif command == "show":
            parser.set_defaults(command_handler=_handle_show, manifest_id=manifest.manifest_id)
        elif command == "run":
            parser.add_argument(
                "--resume",
                action="store_true",
                default=False,
                help="Reuse the most recent persisted run payload for this harness/profile.",
            )
            parser.add_argument(
                "--run",
                dest="resume_run_number",
                type=int,
                help="Specific persisted run number to reuse when --resume is set; defaults to the latest stored run.",
            )
            add_model_selection_options(parser, required=False)
            parser.add_argument(
                "--sink",
                action="append",
                default=[],
                metavar="SPEC",
                help="Add a per-run output sink override using kind:value or kind:key=value,key=value.",
            )
            parser.add_argument("--max-cycles", type=int, help="Optional max cycle count passed to agent.run().")
            parser.add_argument(
                "--run-arg",
                action="append",
                default=[],
                metavar="KEY=VALUE",
                help="Override one persisted harness-specific run-only argument as KEY=VALUE.",
            )
            add_manifest_parameter_options(parser, manifest=manifest, scope="runtime")
            add_manifest_parameter_options(parser, manifest=manifest, scope="custom")
            adapter = _build_adapter(manifest)
            existing_action_ids = {id(action) for action in parser._actions}
            adapter.register_run_arguments(parser)
            adapter_actions = [
                action
                for action in parser._actions
                if id(action) not in existing_action_ids and action.dest not in {argparse.SUPPRESS, None}
            ]
            run_argument_defaults = {
                "max_cycles": None,
                "model_factory": None,
                "sink": [],
            }
            adapter_argument_names: list[str] = []
            for action in adapter_actions:
                run_argument_defaults[action.dest] = action.default
                adapter_argument_names.append(action.dest)
            parser.set_defaults(
                command_handler=_handle_run,
                manifest_id=manifest.manifest_id,
                **{
                    _RUN_ARGUMENT_DEFAULTS_DEST: run_argument_defaults,
                    _RUN_ADAPTER_ARGUMENT_NAMES_DEST: tuple(adapter_argument_names),
                },
            )
        elif command == "inspect":
            parser.set_defaults(command_handler=_handle_inspect, manifest_id=manifest.manifest_id)
        elif command == "credentials_bind":
            parser.add_argument(
                "--env",
                action="append",
                default=[],
                metavar="FAMILY.FIELD=ENV_VAR",
                help="Bind one provider credential field to an env var. Repeat the flag as needed.",
            )
            parser.add_argument("--description", help="Optional description stored with the binding.")
            parser.set_defaults(command_handler=_handle_credentials_bind, manifest_id=manifest.manifest_id)
        elif command == "credentials_show":
            parser.set_defaults(command_handler=_handle_credentials_show, manifest_id=manifest.manifest_id)
        elif command == "credentials_test":
            parser.set_defaults(command_handler=_handle_credentials_test, manifest_id=manifest.manifest_id)
        else:  # pragma: no cover - defensive
            raise ValueError(f"Unsupported platform command '{command}'.")


def _handle_prepare(args: argparse.Namespace) -> int:
    manifest = get_harness_manifest(args.manifest_id)
    adapter = _build_adapter(manifest)
    context = _build_context(
        manifest=manifest,
        adapter=adapter,
        agent_name=args.agent,
        memory_root=args.memory_root,
        incoming_runtime=collect_manifest_parameter_values(args, manifest=manifest, scope="runtime"),
        incoming_custom=collect_manifest_parameter_values(args, manifest=manifest, scope="custom"),
        persist_profile=True,
    )
    payload = _base_payload(context)
    payload["state"] = adapter.show(context)
    payload["status"] = "prepared"
    emit_json(payload)
    return 0


def _handle_show(args: argparse.Namespace) -> int:
    manifest = get_harness_manifest(args.manifest_id)
    adapter = _build_adapter(manifest)
    context = _build_context(
        manifest=manifest,
        adapter=adapter,
        agent_name=args.agent,
        memory_root=args.memory_root,
        incoming_runtime={},
        incoming_custom={},
        persist_profile=False,
    )
    payload = _base_payload(context)
    payload["state"] = adapter.show(context)
    emit_json(payload)
    return 0


def _handle_run(args: argparse.Namespace) -> int:
    manifest = get_harness_manifest(args.manifest_id)
    adapter = _build_adapter(manifest)
    incoming_runtime = collect_manifest_parameter_values(args, manifest=manifest, scope="runtime")
    incoming_custom = collect_manifest_parameter_values(args, manifest=manifest, scope="custom")
    selected_snapshot: HarnessRunSnapshot | None = None
    if args.resume:
        selection_context = _build_context(
            manifest=manifest,
            adapter=adapter,
            agent_name=args.agent,
            memory_root=args.memory_root,
            incoming_runtime={},
            incoming_custom={},
            persist_profile=False,
        )
        selected_snapshot = _resolve_profile_resume_snapshot(
            profile=selection_context.profile,
            run_number=args.resume_run_number,
        )
        context = _build_context(
            manifest=manifest,
            adapter=adapter,
            agent_name=args.agent,
            memory_root=args.memory_root,
            incoming_runtime=incoming_runtime,
            incoming_custom=incoming_custom,
            base_runtime_parameters=selected_snapshot.runtime_parameters,
            base_custom_parameters=selected_snapshot.custom_parameters,
            persist_profile=True,
        )
    else:
        context = _build_context(
            manifest=manifest,
            adapter=adapter,
            agent_name=args.agent,
            memory_root=args.memory_root,
            incoming_runtime=incoming_runtime,
            incoming_custom=incoming_custom,
            persist_profile=True,
        )
    run_request = _resolve_run_request(
        args=args,
        profile=context.profile,
        resume_requested=bool(args.resume),
        resume_snapshot=selected_snapshot,
        requested_run_number=args.resume_run_number,
        run_argument_defaults=getattr(args, _RUN_ARGUMENT_DEFAULTS_DEST, {}),
        adapter_argument_names=getattr(args, _RUN_ADAPTER_ARGUMENT_NAMES_DEST, ()),
        run_argument_overrides=parse_generic_assignments(args.run_arg),
    )
    context = _persist_run_snapshot(context, run_request)
    effective_args = _clone_args_with_run_request(args, run_request)
    return _execute_run(
        adapter=adapter,
        args=effective_args,
        context=context,
        run_request=run_request,
        source_snapshot=selected_snapshot,
    )


def _handle_resume(args: argparse.Namespace) -> int:
    agent_name = _resolve_resume_agent_name(args)
    repo_root = resolve_repo_root(Path.cwd())
    manifest = _resolve_resume_manifest(args.harness)
    candidates = _discover_resume_candidates(repo_root=repo_root, agent_name=agent_name, manifest=manifest)
    if not candidates:
        if manifest is not None:
            raise ValueError(
                f"No resumable profile named '{agent_name}' was found for harness '{manifest.manifest_id}'."
            )
        raise ValueError(f"No resumable profile named '{agent_name}' was found.")
    candidate = _select_resume_candidate(agent_name=agent_name, candidates=candidates)
    adapter = _build_adapter(candidate.manifest)
    selected_snapshot = _resolve_profile_resume_snapshot(
        profile=candidate.profile,
        run_number=args.resume_run_number,
    )
    context = _build_context(
        manifest=candidate.manifest,
        adapter=adapter,
        agent_name=candidate.agent_name,
        memory_path=candidate.memory_path,
        incoming_runtime=_parse_resume_manifest_parameters(args.runtime_param, manifest=candidate.manifest, scope="runtime"),
        incoming_custom=_parse_resume_manifest_parameters(args.custom_param, manifest=candidate.manifest, scope="custom"),
        base_runtime_parameters=selected_snapshot.runtime_parameters,
        base_custom_parameters=selected_snapshot.custom_parameters,
        persist_profile=True,
    )
    run_request = _resolve_resume_request_from_snapshot(
        snapshot=selected_snapshot,
        model_factory=args.model_factory,
        sink_specs=args.sink,
        max_cycles=args.max_cycles,
        run_argument_overrides=parse_generic_assignments(args.run_arg),
    )
    context = _persist_run_snapshot(context, run_request)
    effective_args = argparse.Namespace(
        agent=context.agent_name,
        harness=context.manifest.manifest_id,
        max_cycles=run_request.max_cycles,
        model_factory=run_request.model_factory,
        model=run_request.model_spec,
        model_profile=run_request.model_profile,
        sink=list(run_request.sink_specs),
        **dict(run_request.adapter_arguments),
    )
    return _execute_run(
        adapter=adapter,
        args=effective_args,
        context=context,
        run_request=run_request,
        source_snapshot=selected_snapshot,
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
    model = resolve_agent_model_from_args(args)
    runtime_config = _build_runtime_config(run_request.sink_specs)
    payload = _base_payload(context)
    payload["resume"] = {
        "adapter_arguments": dict(run_request.adapter_arguments),
        "max_cycles": run_request.max_cycles,
        "sink_specs": list(run_request.sink_specs),
    }
    _populate_model_selection_payload(
        payload["resume"],
        model_factory=run_request.model_factory,
        model_spec=run_request.model_spec,
        model_profile=run_request.model_profile,
    )
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


def _handle_inspect(args: argparse.Namespace) -> int:
    manifest = get_harness_manifest(args.manifest_id)
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
    emit_json(
        {
            "harness": manifest.manifest_id,
            "display_name": manifest.display_name,
            "import_path": manifest.import_path,
            "cli_command": manifest.cli_command,
            "cli_adapter_path": manifest.cli_adapter_path,
            "default_memory_root": manifest.resolved_default_memory_root,
            "runtime_parameters": [_render_parameter_spec(spec) for spec in manifest.runtime_parameters],
            "custom_parameters": [_render_parameter_spec(spec) for spec in manifest.custom_parameters],
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
            "provider_credential_fields": credential_fields,
            "output_schema": manifest.output_schema,
        }
    )
    return 0


def _handle_credentials_bind(args: argparse.Namespace) -> int:
    manifest = get_harness_manifest(args.manifest_id)
    repo_root = resolve_repo_root(args.memory_root)
    store = CredentialsConfigStore(repo_root=repo_root)
    binding_name = _binding_name(manifest, args.agent)
    existing_references = _load_existing_binding_references(store, binding_name)
    updated_references = dict(existing_references)
    for assignment in args.env:
        field_name, env_var = _parse_reference_assignment(assignment)
        updated_references[field_name] = env_var
    _validate_binding_references(manifest, updated_references)
    binding = AgentCredentialBinding(
        agent_name=binding_name,
        references=tuple(
            CredentialEnvReference(field_name=field_name, env_var=env_var)
            for field_name, env_var in sorted(updated_references.items())
        ),
        description=args.description,
    )
    config_path = store.upsert(binding)
    emit_json(
        {
            "agent": args.agent,
            "binding_name": binding_name,
            "config_path": str(config_path),
            "families": _group_reference_mapping(updated_references),
            "harness": manifest.manifest_id,
            "status": "bound",
        }
    )
    return 0


def _handle_credentials_show(args: argparse.Namespace) -> int:
    manifest = get_harness_manifest(args.manifest_id)
    repo_root = resolve_repo_root(args.memory_root)
    store = CredentialsConfigStore(repo_root=repo_root)
    binding_name = _binding_name(manifest, args.agent)
    try:
        binding = store.load().binding_for(binding_name)
    except AgentCredentialsNotConfiguredError:
        emit_json(
            {
                "agent": args.agent,
                "binding_name": binding_name,
                "bound": False,
                "harness": manifest.manifest_id,
                "provider_families": list(manifest.provider_families),
            }
        )
        return 0
    mapping = {reference.field_name: reference.env_var for reference in binding.references}
    emit_json(
        {
            "agent": args.agent,
            "binding_name": binding_name,
            "bound": True,
            "config_path": str(store.config_path),
            "description": binding.description,
            "families": _group_reference_mapping(mapping),
            "harness": manifest.manifest_id,
        }
    )
    return 0


def _handle_credentials_test(args: argparse.Namespace) -> int:
    manifest = get_harness_manifest(args.manifest_id)
    repo_root = resolve_repo_root(args.memory_root)
    store = CredentialsConfigStore(repo_root=repo_root)
    binding_name = _binding_name(manifest, args.agent)
    binding = store.load().binding_for(binding_name)
    resolved = store.resolve_binding(binding)
    resolved_by_family = _group_resolved_values(resolved.as_dict())
    payload_by_family: dict[str, Any] = {}
    for family, values in resolved_by_family.items():
        spec = get_provider_credential_spec(family)
        credential_object = spec.build_credentials(values)
        if hasattr(credential_object, "as_redacted_dict"):
            payload_by_family[family] = credential_object.as_redacted_dict()  # type: ignore[assignment]
        else:
            payload_by_family[family] = spec.redact_values(values)
    emit_json(
        {
            "agent": args.agent,
            "binding_name": binding_name,
            "env_path": str(resolved.env_path),
            "families": payload_by_family,
            "harness": manifest.manifest_id,
            "status": "resolved",
        }
    )
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
            model=run_request.model_spec,
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
        override_selection = _resolve_model_selection(
            model_factory=getattr(args, "model_factory", None),
            model_spec=getattr(args, "model", None),
            model_profile=getattr(args, "model_profile", None),
            required=False,
        )
        if _model_selection_provided(override_selection):
            model_selection = override_selection
        else:
            model_selection = _resolve_model_selection(
                model_factory=snapshot.model_factory,
                model_spec=snapshot.model,
                model_profile=snapshot.model_profile,
                required=True,
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
            model_factory=model_selection["model_factory"],
            model_spec=model_selection["model"],
            model_profile=model_selection["model_profile"],
            sink_specs=tuple(sink_specs),
            max_cycles=max_cycles,
            adapter_arguments=adapter_arguments,
        )

    model_selection = _resolve_model_selection(
        model_factory=getattr(args, "model_factory", None),
        model_spec=getattr(args, "model", None),
        model_profile=getattr(args, "model_profile", None),
        required=True,
    )
    adapter_arguments = {argument_name: getattr(args, argument_name) for argument_name in adapter_argument_names}
    adapter_arguments.update(run_argument_overrides)
    return _ResolvedRunRequest(
        model_factory=model_selection["model_factory"],
        model_spec=model_selection["model"],
        model_profile=model_selection["model_profile"],
        sink_specs=tuple(args.sink),
        max_cycles=args.max_cycles,
        adapter_arguments=adapter_arguments,
    )


def _resolve_resume_request_from_snapshot(
    *,
    snapshot: HarnessRunSnapshot | None,
    model_factory: str | None,
    sink_specs: list[str],
    max_cycles: int | None,
    run_argument_overrides: dict[str, Any],
) -> _ResolvedRunRequest:
    if snapshot is None:
        raise ValueError("The selected profile has no persisted run payload to resume.")
    override_selection = _resolve_model_selection(
        model_factory=model_factory,
        model_spec=None,
        model_profile=None,
        required=False,
    )
    if _model_selection_provided(override_selection):
        model_selection = override_selection
    else:
        model_selection = _resolve_model_selection(
            model_factory=snapshot.model_factory,
            model_spec=snapshot.model,
            model_profile=snapshot.model_profile,
            required=True,
        )
    resolved_sink_specs = tuple(sink_specs) if sink_specs else snapshot.sink_specs
    resolved_max_cycles = max_cycles if max_cycles is not None else snapshot.max_cycles
    adapter_arguments = dict(snapshot.adapter_arguments)
    adapter_arguments.update(run_argument_overrides)
    return _ResolvedRunRequest(
        model_factory=model_selection["model_factory"],
        model_spec=model_selection["model"],
        model_profile=model_selection["model_profile"],
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
    payload["model"] = run_request.model_spec
    payload["model_profile"] = run_request.model_profile
    payload["sink"] = list(run_request.sink_specs)
    payload["max_cycles"] = run_request.max_cycles
    payload.update(run_request.adapter_arguments)
    return argparse.Namespace(**payload)


def _resolve_model_selection(
    *,
    model_factory: str | None,
    model_spec: str | None,
    model_profile: str | None,
    required: bool,
) -> dict[str, str | None]:
    normalized = {
        "model_factory": _normalize_optional_value(model_factory),
        "model": _normalize_optional_value(model_spec),
        "model_profile": _normalize_optional_value(model_profile),
    }
    selected_count = sum(1 for value in normalized.values() if value is not None)
    if required:
        if selected_count != 1:
            raise ValueError("Exactly one of --model, --profile, or --model-factory must be provided.")
    elif selected_count > 1:
        raise ValueError("Only one of --model, --profile, or --model-factory may be provided.")
    return normalized


def _model_selection_provided(selection: dict[str, str | None]) -> bool:
    return any(value is not None for value in selection.values())


def _populate_model_selection_payload(
    payload: dict[str, Any],
    *,
    model_factory: str | None,
    model_spec: str | None,
    model_profile: str | None,
) -> None:
    if model_factory is not None:
        payload["model_factory"] = model_factory
    if model_spec is not None:
        payload["model"] = model_spec
    if model_profile is not None:
        payload["model_profile"] = model_profile


def _normalize_optional_value(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
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


def _build_runtime_config(sink_specs: tuple[str, ...] | list[str]) -> AgentRuntimeConfig:
    connections = ConnectionsConfigStore().load().enabled_connections()
    return AgentRuntimeConfig(
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


def _print_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 0


__all__ = ["register_platform_commands"]
