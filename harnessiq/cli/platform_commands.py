"""Platform-first root CLI commands for harness lifecycle and credentials."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

from harnessiq.cli._langsmith import seed_cli_environment
from harnessiq.cli.common import (
    add_agent_options,
    add_manifest_parameter_options,
    add_policy_options,
    build_runtime_config,
    collect_manifest_parameter_values,
    emit_json,
    load_factory,
    resolve_memory_path,
    resolve_repo_root,
)
from harnessiq.cli.adapters import HarnessAdapterContext
from harnessiq.config import (
    AgentCredentialBinding,
    AgentCredentialsNotConfiguredError,
    CredentialEnvReference,
    CredentialsConfigStore,
    HarnessProfile,
    HarnessProfileStore,
    get_provider_credential_spec,
)
from harnessiq.shared.harness_manifest import HarnessManifest
from harnessiq.shared.harness_manifests import get_harness_manifest, list_harness_manifests


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
                "--model-factory",
                required=True,
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
            add_manifest_parameter_options(parser, manifest=manifest, scope="runtime")
            add_manifest_parameter_options(parser, manifest=manifest, scope="custom")
            add_policy_options(parser)
            _build_adapter(manifest).register_run_arguments(parser)
            parser.set_defaults(command_handler=_handle_run, manifest_id=manifest.manifest_id)
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
    context = _build_context(
        manifest=manifest,
        adapter=adapter,
        agent_name=args.agent,
        memory_root=args.memory_root,
        incoming_runtime=collect_manifest_parameter_values(args, manifest=manifest, scope="runtime"),
        incoming_custom=collect_manifest_parameter_values(args, manifest=manifest, scope="custom"),
        persist_profile=True,
    )
    seed_cli_environment(context.repo_root)
    model = load_factory(args.model_factory)()
    if not hasattr(model, "generate_turn"):
        raise TypeError("Model factory must return an object that implements generate_turn(request).")
    runtime_config = build_runtime_config(
        sink_specs=args.sink,
        approval_policy=args.approval_policy,
        allowed_tools=args.allowed_tools,
    )
    payload = _base_payload(context)
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
    memory_root: str,
    incoming_runtime: dict[str, Any],
    incoming_custom: dict[str, Any],
    persist_profile: bool,
) -> HarnessAdapterContext:
    memory_root_path = Path(memory_root).expanduser()
    memory_path = resolve_memory_path(agent_name, memory_root_path)
    repo_root = resolve_repo_root(memory_root_path)
    seed_profile = HarnessProfile(
        manifest_id=manifest.manifest_id,
        agent_name=agent_name,
    )
    preliminary_context = HarnessAdapterContext(
        manifest=manifest,
        agent_name=agent_name,
        memory_path=memory_path,
        repo_root=repo_root,
        profile=seed_profile,
        runtime_parameters={},
        custom_parameters={},
        bound_credentials={},
    )
    adapter.prepare(preliminary_context)
    native_runtime, native_custom = adapter.load_native_parameters(preliminary_context)
    profile_store = HarnessProfileStore(memory_path)
    if profile_store.profile_path.exists():
        profile = profile_store.load(manifest_id=manifest.manifest_id, agent_name=agent_name)
    else:
        profile = HarnessProfile(
            manifest_id=manifest.manifest_id,
            agent_name=agent_name,
            runtime_parameters=native_runtime,
            custom_parameters=native_custom,
        )
    if incoming_runtime:
        next_runtime = dict(profile.runtime_parameters)
        next_runtime.update(incoming_runtime)
    else:
        next_runtime = dict(profile.runtime_parameters)
    if incoming_custom:
        next_custom = dict(profile.custom_parameters)
        next_custom.update(incoming_custom)
    else:
        next_custom = dict(profile.custom_parameters)
    profile = HarnessProfile(
        manifest_id=manifest.manifest_id,
        agent_name=agent_name,
        runtime_parameters=next_runtime,
        custom_parameters=next_custom,
    )
    if persist_profile:
        profile_store.save(profile)
    runtime_parameters = manifest.resolve_runtime_parameters(profile.runtime_parameters)
    custom_parameters = manifest.resolve_custom_parameters(profile.custom_parameters)
    context = HarnessAdapterContext(
        manifest=manifest,
        agent_name=agent_name,
        memory_path=memory_path,
        repo_root=repo_root,
        profile=profile,
        runtime_parameters=runtime_parameters,
        custom_parameters=custom_parameters,
        bound_credentials=_resolve_bound_credentials(manifest, agent_name, repo_root),
    )
    adapter.synchronize_profile(context)
    return context


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
