"""Leads agent CLI commands for managed configuration and execution."""

from __future__ import annotations

import argparse
import importlib
import json
import re
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from harnessiq.agents import LeadsAgent
from harnessiq.cli._langsmith import seed_langsmith_environment
from harnessiq.shared.leads import LeadICP, LeadRunConfig, LeadsMemoryStore, LeadsStorageBackend

SUPPORTED_LEADS_RUNTIME_PARAMETERS = (
    "max_tokens",
    "reset_threshold",
    "prune_search_interval",
    "prune_token_limit",
    "search_summary_every",
    "search_tail_size",
    "max_leads_per_icp",
)
_RUN_CONFIG_KEYS = frozenset({"search_summary_every", "search_tail_size", "max_leads_per_icp"})
_RUNTIME_PARAMETERS_FILENAME = "runtime_parameters.json"


def register_leads_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser("leads", help="Manage and run the leads discovery agent")
    parser.set_defaults(command_handler=lambda args: _print_help(parser))
    leads_subparsers = parser.add_subparsers(dest="leads_command")

    prepare_parser = leads_subparsers.add_parser("prepare", help="Create or refresh a leads agent memory folder")
    _add_agent_options(prepare_parser)
    prepare_parser.set_defaults(command_handler=_handle_prepare)

    configure_parser = leads_subparsers.add_parser(
        "configure",
        help="Write company background, ICPs, platforms, and leads runtime configuration",
    )
    _add_agent_options(configure_parser)
    _add_text_or_file_options(configure_parser, "company_background", "Company background")
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
        help=f"Persist a leads runtime/config parameter. Supported keys: {', '.join(SUPPORTED_LEADS_RUNTIME_PARAMETERS)}.",
    )
    configure_parser.set_defaults(command_handler=_handle_configure)

    show_parser = leads_subparsers.add_parser("show", help="Render the current leads agent state as JSON")
    _add_agent_options(show_parser)
    show_parser.set_defaults(command_handler=_handle_show)

    run_parser = leads_subparsers.add_parser("run", help="Run the leads SDK agent from persisted CLI state")
    _add_agent_options(run_parser)
    run_parser.add_argument(
        "--model-factory",
        required=True,
        help="Import path in the form module:callable that returns an AgentModel instance.",
    )
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
    _emit_json(
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

    company_background = _resolve_text_argument(
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

    normalized_parameters = normalize_leads_runtime_parameters(_parse_generic_assignments(args.runtime_param))
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
    _emit_json(payload)
    return 0


def _handle_show(args: argparse.Namespace) -> int:
    store = _load_store(args)
    store.prepare()
    _ensure_runtime_parameters_file(store.memory_path)
    _emit_json(_build_summary(store))
    return 0


def _handle_run(args: argparse.Namespace) -> int:
    store = _load_store(args)
    store.prepare()
    _ensure_runtime_parameters_file(store.memory_path)
    seed_langsmith_environment(Path(args.memory_root).expanduser())
    run_config = store.read_run_config()
    overrides = normalize_leads_runtime_parameters(_parse_generic_assignments(args.runtime_param))
    effective_run_config = _apply_run_config_overrides(run_config, overrides)

    runtime_parameters = _read_runtime_parameters(store.memory_path)
    runtime_parameters.update({key: value for key, value in overrides.items() if key not in _RUN_CONFIG_KEYS})

    model = _load_factory(args.model_factory)()
    if not hasattr(model, "generate_turn"):
        raise TypeError("Model factory must return an object that implements generate_turn(request).")

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

    _emit_json(
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


def _add_agent_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--agent", required=True, help="Logical leads agent name used to resolve the memory folder.")
    parser.add_argument(
        "--memory-root",
        default="memory/leads",
        help="Root directory that holds per-agent leads memory folders.",
    )


def _add_text_or_file_options(parser: argparse.ArgumentParser, field_name: str, label: str) -> None:
    group = parser.add_mutually_exclusive_group()
    option_name = field_name.replace("_", "-")
    group.add_argument(f"--{option_name}-text", help=f"{label} content provided inline.")
    group.add_argument(f"--{option_name}-file", help=f"Path to a UTF-8 text file containing {label.lower()} content.")


def _load_store(args: argparse.Namespace) -> LeadsMemoryStore:
    return LeadsMemoryStore(memory_path=_resolve_memory_path(args.agent, args.memory_root))


def _resolve_memory_path(agent_name: str, memory_root: str) -> Path:
    return Path(memory_root).expanduser() / _slugify_agent_name(agent_name)


def _slugify_agent_name(agent_name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", agent_name.strip()).strip("-")
    if not cleaned:
        raise ValueError("Agent names must contain at least one alphanumeric character.")
    return cleaned


def _resolve_text_argument(text_value: str | None, file_value: str | None) -> str | None:
    if text_value is not None:
        return text_value
    if file_value is not None:
        return Path(file_value).read_text(encoding="utf-8")
    return None


def _collect_icp_values(text_values: Sequence[str], file_values: Sequence[str]) -> list[str]:
    icps = [value.strip() for value in text_values if value.strip()]
    for file_value in file_values:
        for raw_line in Path(file_value).read_text(encoding="utf-8").splitlines():
            stripped = raw_line.strip()
            if stripped:
                icps.append(stripped)
    return icps


def _parse_generic_assignments(assignments: Sequence[str]) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for assignment in assignments:
        key, raw_value = _split_assignment(assignment)
        parsed[key] = _parse_scalar(raw_value)
    return parsed


def _parse_factory_assignments(assignments: Sequence[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for assignment in assignments:
        family, spec = _split_assignment(assignment)
        parsed[_normalize_platform_name(family)] = spec
    return parsed


def _split_assignment(assignment: str) -> tuple[str, str]:
    key, separator, value = assignment.partition("=")
    if not separator:
        raise ValueError(f"Expected KEY=VALUE assignment, received '{assignment}'.")
    normalized_key = key.strip()
    if not normalized_key:
        raise ValueError(f"Expected a non-empty key in assignment '{assignment}'.")
    return normalized_key, value


def _parse_scalar(value: str) -> Any:
    trimmed = value.strip()
    if not trimmed:
        return ""
    try:
        return json.loads(trimmed)
    except json.JSONDecodeError:
        return value


def _read_run_config_payload(store: LeadsMemoryStore) -> dict[str, Any]:
    if not store.run_config_path.exists():
        return {}
    return store.read_run_config().as_dict()


def _runtime_parameters_path(memory_path: Path) -> Path:
    return memory_path / _RUNTIME_PARAMETERS_FILENAME


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


def _emit_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _print_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 0


def _normalize_platform_name(value: str) -> str:
    return value.strip().lower()


def normalize_leads_runtime_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    coercers = {
        "max_tokens": _coerce_int,
        "reset_threshold": _coerce_float,
        "prune_search_interval": _coerce_optional_int,
        "prune_token_limit": _coerce_optional_int,
        "search_summary_every": _coerce_int,
        "search_tail_size": _coerce_int,
        "max_leads_per_icp": _coerce_optional_int,
    }
    for key, value in parameters.items():
        if key not in coercers:
            raise ValueError(
                f"Unsupported leads runtime parameter '{key}'. "
                f"Supported: {', '.join(sorted(coercers))}."
            )
        normalized[key] = coercers[key](value)
    return normalized


def _coerce_int(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("Boolean values are not valid integer runtime parameters.")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        return int(value)
    raise ValueError("Runtime parameter must be an integer.")


def _coerce_optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return _coerce_int(value)


def _coerce_float(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("Boolean values are not valid float runtime parameters.")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        return float(value)
    raise ValueError("Runtime parameter must be a float.")


__all__ = [
    "SUPPORTED_LEADS_RUNTIME_PARAMETERS",
    "normalize_leads_runtime_parameters",
    "register_leads_commands",
]
