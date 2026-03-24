"""Leads agent CLI commands for managed configuration and execution."""

from __future__ import annotations

import argparse
import importlib
import json
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from harnessiq.agents import LeadsAgent
from harnessiq.cli._langsmith import seed_cli_environment
from harnessiq.cli.common import (
    add_agent_options,
    add_model_selection_options,
    add_text_or_file_options,
    emit_json,
    format_manifest_parameter_keys,
    parse_manifest_parameter_assignments,
    resolve_agent_model_from_args,
    resolve_memory_path,
    resolve_text_argument,
    split_assignment,
)
from harnessiq.shared.leads import (
    LEADS_HARNESS_MANIFEST,
    RUNTIME_PARAMETERS_FILENAME,
    LeadICP,
    LeadRunConfig,
    LeadsMemoryStore,
    LeadsStorageBackend,
)

SUPPORTED_LEADS_RUNTIME_PARAMETERS = LEADS_HARNESS_MANIFEST.runtime_parameter_names
_RUN_CONFIG_KEYS = frozenset({"search_summary_every", "search_tail_size", "max_leads_per_icp"})


def register_leads_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser("leads", help="Manage and run the leads discovery agent")
    parser.set_defaults(command_handler=lambda args: _print_help(parser))
    leads_subparsers = parser.add_subparsers(dest="leads_command")

    prepare_parser = leads_subparsers.add_parser("prepare", help="Create or refresh a leads agent memory folder")
    add_agent_options(
        prepare_parser,
        agent_help="Logical leads agent name used to resolve the memory folder.",
        memory_root_default="memory/leads",
        memory_root_help="Root directory that holds per-agent leads memory folders.",
    )
    prepare_parser.set_defaults(command_handler=_handle_prepare)

    configure_parser = leads_subparsers.add_parser(
        "configure",
        help="Write company background, ICPs, platforms, and leads runtime configuration",
    )
    add_agent_options(
        configure_parser,
        agent_help="Logical leads agent name used to resolve the memory folder.",
        memory_root_default="memory/leads",
        memory_root_help="Root directory that holds per-agent leads memory folders.",
    )
    add_text_or_file_options(configure_parser, "company_background", "Company background")
    configure_parser.add_argument(
        "--icp-text",
        action="append",
        default=[],
        metavar="TEXT",
        help="Append an ICP definition provided inline. May be passed multiple times.",
    )
    configure_parser.add_argument(
        "--icp-file",
        action="append",
        default=[],
        metavar="PATH",
        help="Path to a UTF-8 file containing one ICP definition per non-empty line.",
    )
    configure_parser.add_argument(
        "--platform",
        action="append",
        default=[],
        metavar="FAMILY",
        help="Provider family to enable (for example: apollo, leadiq, zoominfo). May be passed multiple times.",
    )
    configure_parser.add_argument(
        "--runtime-param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help=(
            "Persist a leads runtime/config parameter. Supported keys: "
            f"{format_manifest_parameter_keys(LEADS_HARNESS_MANIFEST, scope='runtime')}."
        ),
    )
    configure_parser.set_defaults(command_handler=_handle_configure)

    show_parser = leads_subparsers.add_parser("show", help="Render the current leads agent state as JSON")
    add_agent_options(
        show_parser,
        agent_help="Logical leads agent name used to resolve the memory folder.",
        memory_root_default="memory/leads",
        memory_root_help="Root directory that holds per-agent leads memory folders.",
    )
    show_parser.set_defaults(command_handler=_handle_show)

    run_parser = leads_subparsers.add_parser("run", help="Run the leads SDK agent from persisted CLI state")
    add_agent_options(
        run_parser,
        agent_help="Logical leads agent name used to resolve the memory folder.",
        memory_root_default="memory/leads",
        memory_root_help="Root directory that holds per-agent leads memory folders.",
    )
    add_model_selection_options(run_parser)
    run_parser.add_argument(
        "--provider-tools-factory",
        help="Optional import path in the form module:callable that returns an iterable of provider tools.",
    )
    run_parser.add_argument(
        "--provider-credentials-factory",
        action="append",
        default=[],
        metavar="FAMILY=MODULE:CALLABLE",
        help="Map a provider family to a credentials factory. May be passed multiple times.",
    )
    run_parser.add_argument(
        "--provider-client-factory",
        action="append",
        default=[],
        metavar="FAMILY=MODULE:CALLABLE",
        help="Map a provider family to a prebuilt client factory. May be passed multiple times.",
    )
    run_parser.add_argument(
        "--storage-backend-factory",
        help="Optional import path in the form module:callable that returns a LeadsStorageBackend instance.",
    )
    run_parser.add_argument(
        "--runtime-param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Override a persisted leads runtime/config parameter for this run only.",
    )
    run_parser.add_argument("--max-cycles", type=int, help="Optional max cycle count passed to agent.run().")
    run_parser.set_defaults(command_handler=_handle_run)


def _handle_prepare(args: argparse.Namespace) -> int:
    store = _load_store(args)
    store.prepare()
    _ensure_runtime_parameters_file(store.memory_path)
    emit_json(
        {
            "agent": args.agent,
            "memory_path": str(store.memory_path.resolve()),
            "status": "prepared",
        }
    )
    return 0


def _handle_configure(args: argparse.Namespace) -> int:
    store = _load_store(args)
    store.prepare()
    _ensure_runtime_parameters_file(store.memory_path)
    updated: list[str] = []

    config_payload = _read_run_config_payload(store)
    runtime_parameters = _read_runtime_parameters(store.memory_path)

    company_background = resolve_text_argument(
        getattr(args, "company_background_text", None),
        getattr(args, "company_background_file", None),
    )
    if company_background is not None:
        config_payload["company_background"] = company_background
        updated.append("company_background")

    icp_values = _collect_icp_values(args.icp_text, args.icp_file)
    if icp_values:
        config_payload["icps"] = [LeadICP(label=value).as_dict() for value in icp_values]
        updated.append("icps")

    if args.platform:
        config_payload["platforms"] = [_normalize_platform_name(value) for value in args.platform]
        updated.append("platforms")

    normalized_parameters = parse_manifest_parameter_assignments(
        args.runtime_param,
        manifest=LEADS_HARNESS_MANIFEST,
        scope="runtime",
    )
    for key, value in normalized_parameters.items():
        if key in _RUN_CONFIG_KEYS:
            config_payload[key] = value
        else:
            runtime_parameters[key] = value
    if normalized_parameters:
        updated.append("runtime_parameters")

    if config_payload:
        required = {"company_background", "icps", "platforms"}
        missing = sorted(key for key in required if not config_payload.get(key))
        if missing:
            raise ValueError(
                f"Leads configuration is incomplete. Missing: {', '.join(missing)}."
            )
        run_config = LeadRunConfig.from_dict(config_payload)
        store.write_run_config(run_config)
        store.initialize_icp_states(run_config.icps)

    _write_runtime_parameters(store.memory_path, runtime_parameters)
    payload = _build_summary(store)
    payload["updated"] = updated
    payload["status"] = "configured"
    emit_json(payload)
    return 0


def _handle_show(args: argparse.Namespace) -> int:
    store = _load_store(args)
    store.prepare()
    _ensure_runtime_parameters_file(store.memory_path)
    emit_json(_build_summary(store))
    return 0


def _handle_run(args: argparse.Namespace) -> int:
    store = _load_store(args)
    store.prepare()
    _ensure_runtime_parameters_file(store.memory_path)
    seed_cli_environment(Path(args.memory_root).expanduser())
    run_config = store.read_run_config()
    overrides = parse_manifest_parameter_assignments(
        args.runtime_param,
        manifest=LEADS_HARNESS_MANIFEST,
        scope="runtime",
    )
    effective_run_config = _apply_run_config_overrides(run_config, overrides)

    runtime_parameters = _read_runtime_parameters(store.memory_path)
    runtime_parameters.update({key: value for key, value in overrides.items() if key not in _RUN_CONFIG_KEYS})

    model = resolve_agent_model_from_args(args)

    tools = None
    if args.provider_tools_factory:
        created_tools = _load_factory(args.provider_tools_factory)()
        if created_tools is None:
            tools = ()
        elif isinstance(created_tools, (str, bytes)):
            raise TypeError("Provider tools factory must return an iterable of tool objects, not a string.")
        else:
            tools = tuple(created_tools)

    provider_credentials = {
        family: _load_factory(spec)()
        for family, spec in _parse_factory_assignments(args.provider_credentials_factory).items()
    }
    provider_clients = {
        family: _load_factory(spec)()
        for family, spec in _parse_factory_assignments(args.provider_client_factory).items()
    }
    storage_backend = None
    if args.storage_backend_factory:
        storage_backend = _load_factory(args.storage_backend_factory)()
        if not isinstance(storage_backend, LeadsStorageBackend):
            raise TypeError(
                "Storage backend factory must return an object that satisfies the LeadsStorageBackend protocol."
            )

    agent = LeadsAgent(
        model=model,
        company_background=effective_run_config.company_background,
        icps=effective_run_config.icps,
        platforms=effective_run_config.platforms,
        memory_path=store.memory_path,
        storage_backend=storage_backend,
        tools=tools,
        provider_credentials=provider_credentials or None,
        provider_clients=provider_clients or None,
        max_tokens=int(runtime_parameters.get("max_tokens", 80_000)),
        reset_threshold=float(runtime_parameters.get("reset_threshold", 0.9)),
        prune_search_interval=int(runtime_parameters["prune_search_interval"]) if runtime_parameters.get("prune_search_interval") is not None else None,
        prune_token_limit=int(runtime_parameters["prune_token_limit"]) if runtime_parameters.get("prune_token_limit") is not None else None,
        search_summary_every=effective_run_config.search_summary_every,
        search_tail_size=effective_run_config.search_tail_size,
        max_leads_per_icp=effective_run_config.max_leads_per_icp,
    )
    result = agent.run(max_cycles=args.max_cycles)

    emit_json(
        {
            "agent": args.agent,
            "memory_path": str(store.memory_path.resolve()),
            "result": {
                "cycles_completed": result.cycles_completed,
                "pause_reason": result.pause_reason,
                "resets": result.resets,
                "status": result.status,
            },
            "run_state": store.read_run_state().as_dict() if store.run_state_path.exists() else None,
        }
    )
    return 0


def _load_store(args: argparse.Namespace) -> LeadsMemoryStore:
    return LeadsMemoryStore(memory_path=resolve_memory_path(args.agent, args.memory_root))


def _collect_icp_values(text_values: Sequence[str], file_values: Sequence[str]) -> list[str]:
    icps = [value.strip() for value in text_values if value.strip()]
    for file_value in file_values:
        for raw_line in Path(file_value).read_text(encoding="utf-8").splitlines():
            stripped = raw_line.strip()
            if stripped:
                icps.append(stripped)
    return icps


def _parse_factory_assignments(assignments: Sequence[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for assignment in assignments:
        family, spec = split_assignment(assignment)
        parsed[_normalize_platform_name(family)] = spec
    return parsed


def _read_run_config_payload(store: LeadsMemoryStore) -> dict[str, Any]:
    if not store.run_config_path.exists():
        return {}
    return store.read_run_config().as_dict()


def _runtime_parameters_path(memory_path: Path) -> Path:
    return memory_path / RUNTIME_PARAMETERS_FILENAME


def _ensure_runtime_parameters_file(memory_path: Path) -> None:
    path = _runtime_parameters_path(memory_path)
    if not path.exists():
        path.write_text(json.dumps({}, indent=2, sort_keys=True), encoding="utf-8")


def _read_runtime_parameters(memory_path: Path) -> dict[str, Any]:
    path = _runtime_parameters_path(memory_path)
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in '{path.name}'.")
    return dict(payload)


def _write_runtime_parameters(memory_path: Path, payload: dict[str, Any]) -> None:
    path = _runtime_parameters_path(memory_path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _build_summary(store: LeadsMemoryStore) -> dict[str, Any]:
    run_config = store.read_run_config().as_dict() if store.run_config_path.exists() else None
    run_state = store.read_run_state().as_dict() if store.run_state_path.exists() else None
    icp_states = [state.as_dict() for state in store.list_icp_states()]
    return {
        "memory_path": str(store.memory_path.resolve()),
        "run_config": run_config,
        "run_state": run_state,
        "runtime_parameters": _read_runtime_parameters(store.memory_path),
        "icp_states": icp_states,
    }


def _apply_run_config_overrides(
    run_config: LeadRunConfig,
    overrides: dict[str, Any],
) -> LeadRunConfig:
    if not overrides:
        return run_config
    payload = run_config.as_dict()
    for key in _RUN_CONFIG_KEYS:
        if key in overrides:
            payload[key] = overrides[key]
    return LeadRunConfig.from_dict(payload)


def _load_factory(spec: str):
    module_name, separator, attribute_path = spec.partition(":")
    if not separator or not module_name or not attribute_path:
        raise ValueError(f"Factory import paths must use the form module:callable. Received '{spec}'.")
    module = importlib.import_module(module_name)
    target: Any = module
    for attribute_name in attribute_path.split("."):
        target = getattr(target, attribute_name)
    if not callable(target):
        raise TypeError(f"Imported object '{spec}' is not callable.")
    return target


def _print_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 0


def _normalize_platform_name(value: str) -> str:
    return value.strip().lower()


def normalize_leads_runtime_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    return LEADS_HARNESS_MANIFEST.coerce_runtime_parameters(parameters)


__all__ = [
    "SUPPORTED_LEADS_RUNTIME_PARAMETERS",
    "normalize_leads_runtime_parameters",
    "register_leads_commands",
]
