"""Platform-first root CLI commands for harness lifecycle and credentials."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from harnessiq.cli.common import (
    add_agent_options,
    add_manifest_parameter_options,
    collect_manifest_parameter_values,
    emit_json,
    parse_generic_assignments,
    resolve_repo_root,
)
from harnessiq.cli.commands.command_helpers import (
    _base_payload,
    _binding_name,
    _build_adapter,
    _build_context,
    _clone_args_with_run_request,
    _discover_resume_candidates,
    _execute_run,
    _group_reference_mapping,
    _group_resolved_values,
    _load_existing_binding_references,
    _parse_reference_assignment,
    _parse_resume_manifest_parameters,
    _persist_run_snapshot,
    _render_parameter_spec,
    _resolve_profile_resume_snapshot,
    _resolve_resume_agent_name,
    _resolve_resume_manifest,
    _resolve_resume_request_from_snapshot,
    _resolve_run_request,
    _select_resume_candidate,
    _validate_binding_references,
)
from harnessiq.config import (
    AgentCredentialBinding,
    AgentCredentialsNotConfiguredError,
    CredentialEnvReference,
    CredentialsConfigStore,
    HarnessRunSnapshot,
    get_provider_credential_spec,
)
from harnessiq.shared.harness_manifests import get_harness_manifest, list_harness_manifests

_RUN_ARGUMENT_DEFAULTS_DEST = "_run_argument_defaults"
_RUN_ADAPTER_ARGUMENT_NAMES_DEST = "_run_adapter_argument_names"


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
            parser.add_argument(
                "--model-factory",
                help="Import path in the form module:callable that returns an AgentModel instance.",
            )
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


def _print_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 0


__all__ = ["register_platform_commands"]
