"""CLI commands for the Instagram keyword discovery agent."""

from __future__ import annotations

import argparse
import importlib
import json
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from harnessiq.cli._langsmith import seed_cli_environment
from harnessiq.cli.common import (
    add_agent_options,
    add_policy_options,
    add_model_selection_options,
    add_text_or_file_options,
    build_runtime_config,
    emit_json,
    format_manifest_parameter_keys,
    parse_manifest_parameter_assignments,
    resolve_agent_model_from_args,
    resolve_memory_path,
    resolve_text_argument,
)
from harnessiq.shared.instagram import (
    INSTAGRAM_HARNESS_MANIFEST,
    InstagramMemoryStore,
    normalize_instagram_custom_parameters,
    normalize_instagram_runtime_parameters,
    resolve_instagram_icp_profiles,
)

SUPPORTED_INSTAGRAM_RUNTIME_PARAMETERS = INSTAGRAM_HARNESS_MANIFEST.runtime_parameter_names
SUPPORTED_INSTAGRAM_CUSTOM_PARAMETERS = INSTAGRAM_HARNESS_MANIFEST.custom_parameter_names

_DEFAULT_SEARCH_BACKEND_FACTORY = "harnessiq.integrations.instagram_playwright:create_search_backend"


def register_instagram_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser("instagram", help="Manage and run the Instagram keyword discovery agent")
    parser.set_defaults(command_handler=lambda args: _print_help(parser))
    instagram_subparsers = parser.add_subparsers(dest="instagram_command")

    prepare_parser = instagram_subparsers.add_parser(
        "prepare",
        help="Create or refresh an Instagram agent memory folder",
    )
    add_agent_options(
        prepare_parser,
        agent_help="Logical agent name used to resolve the memory folder.",
        memory_root_default="memory/instagram",
        memory_root_help="Root directory that holds per-agent instagram memory folders.",
    )
    prepare_parser.set_defaults(command_handler=_handle_prepare)

    configure_parser = instagram_subparsers.add_parser(
        "configure",
        help="Persist ICPs, identity, prompt text, and runtime parameters for the Instagram agent",
    )
    add_agent_options(
        configure_parser,
        agent_help="Logical agent name used to resolve the memory folder.",
        memory_root_default="memory/instagram",
        memory_root_help="Root directory that holds per-agent instagram memory folders.",
    )
    configure_parser.add_argument(
        "--icp",
        action="append",
        default=[],
        help="One ICP description. Repeat the flag to provide multiple ICPs.",
    )
    configure_parser.add_argument(
        "--icp-file",
        help="Path to a JSON array or newline-delimited UTF-8 text file containing ICP descriptions.",
    )
    add_text_or_file_options(configure_parser, "agent_identity", "Agent identity")
    add_text_or_file_options(configure_parser, "additional_prompt", "Additional prompt")
    configure_parser.add_argument(
        "--runtime-param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help=(
            f"Persist a runtime parameter. Supported keys: "
            f"{format_manifest_parameter_keys(INSTAGRAM_HARNESS_MANIFEST, scope='runtime')}."
        ),
    )
    configure_parser.add_argument(
        "--custom-param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Persist an Instagram custom parameter as KEY=VALUE. Values are parsed as JSON when possible.",
    )
    configure_parser.set_defaults(command_handler=_handle_configure)

    show_parser = instagram_subparsers.add_parser(
        "show",
        help="Render the current Instagram agent state as JSON",
    )
    add_agent_options(
        show_parser,
        agent_help="Logical agent name used to resolve the memory folder.",
        memory_root_default="memory/instagram",
        memory_root_help="Root directory that holds per-agent instagram memory folders.",
    )
    show_parser.set_defaults(command_handler=_handle_show)

    run_parser = instagram_subparsers.add_parser(
        "run",
        help="Run the Instagram keyword discovery agent from persisted memory",
    )
    add_agent_options(
        run_parser,
        agent_help="Logical agent name used to resolve the memory folder.",
        memory_root_default="memory/instagram",
        memory_root_help="Root directory that holds per-agent instagram memory folders.",
    )
    add_model_selection_options(run_parser)
    run_parser.add_argument(
        "--search-backend-factory",
        default=_DEFAULT_SEARCH_BACKEND_FACTORY,
        help=(
            "Import path (module:callable) that returns an InstagramSearchBackend instance. "
            f"Defaults to {_DEFAULT_SEARCH_BACKEND_FACTORY}."
        ),
    )
    run_parser.add_argument(
        "--runtime-param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Override a persisted runtime parameter for this run only.",
    )
    run_parser.add_argument(
        "--custom-param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Override a persisted custom parameter for this run only.",
    )
    run_parser.add_argument(
        "--icp",
        action="append",
        default=[],
        help="One ICP description to use for this run. Repeat the flag to provide multiple ICPs.",
    )
    run_parser.add_argument(
        "--icp-file",
        help="Path to a JSON array or newline-delimited UTF-8 text file containing ICP descriptions for this run.",
    )
    run_parser.add_argument("--max-cycles", type=int, help="Optional max cycle count passed to agent.run().")
    add_policy_options(run_parser)
    run_parser.set_defaults(command_handler=_handle_run)

    get_emails_parser = instagram_subparsers.add_parser(
        "get-emails",
        help="Return all persisted discovered emails for the configured Instagram agent",
    )
    add_agent_options(
        get_emails_parser,
        agent_help="Logical agent name used to resolve the memory folder.",
        memory_root_default="memory/instagram",
        memory_root_help="Root directory that holds per-agent instagram memory folders.",
    )
    get_emails_parser.set_defaults(command_handler=_handle_get_emails)


def _handle_prepare(args: argparse.Namespace) -> int:
    store = _load_store(args)
    store.prepare()
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
    updated: list[str] = []

    icp_profiles = _resolve_icp_input(args.icp, args.icp_file)
    if icp_profiles is not None:
        store.write_icp_profiles(icp_profiles)
        updated.append("icp_profiles")

    agent_identity = resolve_text_argument(
        getattr(args, "agent_identity_text", None),
        getattr(args, "agent_identity_file", None),
    )
    if agent_identity is not None:
        store.write_agent_identity(agent_identity)
        updated.append("agent_identity")

    additional_prompt = resolve_text_argument(
        getattr(args, "additional_prompt_text", None),
        getattr(args, "additional_prompt_file", None),
    )
    if additional_prompt is not None:
        store.write_additional_prompt(additional_prompt)
        updated.append("additional_prompt")

    runtime_parameters = _parse_runtime_assignments(args.runtime_param)
    if runtime_parameters:
        current = store.read_runtime_parameters()
        current.update(runtime_parameters)
        store.write_runtime_parameters(current)
        updated.append("runtime_parameters")

    custom_parameters = _parse_custom_assignments(args.custom_param)
    if custom_parameters:
        current_custom = store.read_custom_parameters()
        current_custom.update(custom_parameters)
        store.write_custom_parameters(current_custom)
        updated.append("custom_parameters")

    payload = _build_summary(store)
    payload["status"] = "configured"
    payload["updated"] = updated
    emit_json(payload)
    return 0


def _handle_show(args: argparse.Namespace) -> int:
    store = _load_store(args)
    store.prepare()
    emit_json(_build_summary(store))
    return 0


def _handle_run(args: argparse.Namespace) -> int:
    from harnessiq.agents.instagram import InstagramKeywordDiscoveryAgent

    store = _load_store(args)
    store.prepare()
    seed_cli_environment(Path(args.memory_root).expanduser())

    model = resolve_agent_model_from_args(args)

    browser_data_dir = store.memory_path / "browser-data"
    if "HARNESSIQ_INSTAGRAM_SESSION_DIR" not in os.environ:
        os.environ["HARNESSIQ_INSTAGRAM_SESSION_DIR"] = str(browser_data_dir.resolve())

    search_backend = _load_factory(args.search_backend_factory)()
    runtime_overrides = _parse_runtime_assignments(args.runtime_param)
    custom_overrides = _parse_custom_assignments(args.custom_param)
    icp_profiles = _resolve_icp_input(args.icp, args.icp_file)
    if icp_profiles is not None:
        custom_overrides["icp_profiles"] = icp_profiles

    agent = InstagramKeywordDiscoveryAgent.from_memory(
        model=model,
        search_backend=search_backend,
        memory_path=store.memory_path,
        runtime_overrides=runtime_overrides,
        custom_overrides=custom_overrides,
        runtime_config=build_runtime_config(
            approval_policy=args.approval_policy,
            allowed_tools=args.allowed_tools,
        ),
    )
    result = agent.run(max_cycles=args.max_cycles)
    emit_json(
        {
            "agent": args.agent,
            "email_count": len(agent.get_emails()),
            "memory_path": str(store.memory_path.resolve()),
            "result": {
                "cycles_completed": result.cycles_completed,
                "pause_reason": result.pause_reason,
                "resets": result.resets,
                "status": result.status,
            },
        }
    )
    return 0


def _handle_get_emails(args: argparse.Namespace) -> int:
    store = _load_store(args)
    store.prepare()
    emails = store.get_emails()
    emit_json(
        {
            "agent": args.agent,
            "count": len(emails),
            "emails": emails,
            "memory_path": str(store.memory_path.resolve()),
        }
    )
    return 0


def _load_store(args: argparse.Namespace) -> InstagramMemoryStore:
    return InstagramMemoryStore(memory_path=resolve_memory_path(args.agent, args.memory_root))


def _resolve_icp_input(inline_values: Sequence[str], file_value: str | None) -> list[str] | None:
    cleaned_inline = [value.strip() for value in inline_values if value and value.strip()]
    if file_value is None:
        return cleaned_inline or None
    raw = Path(file_value).read_text(encoding="utf-8").strip()
    if not raw:
        return []
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return [line.strip() for line in raw.splitlines() if line.strip()]
    if not isinstance(payload, list):
        raise ValueError("ICP file must be a JSON array or newline-delimited text file.")
    return [str(value).strip() for value in payload if str(value).strip()]


def _parse_runtime_assignments(assignments: Sequence[str]) -> dict[str, Any]:
    return parse_manifest_parameter_assignments(
        assignments,
        manifest=INSTAGRAM_HARNESS_MANIFEST,
        scope="runtime",
    )


def _parse_custom_assignments(assignments: Sequence[str]) -> dict[str, Any]:
    return parse_manifest_parameter_assignments(
        assignments,
        manifest=INSTAGRAM_HARNESS_MANIFEST,
        scope="custom",
    )


def _build_summary(store: InstagramMemoryStore) -> dict[str, Any]:
    search_history = store.read_search_history()
    lead_database = store.read_lead_database()
    custom_parameters = store.read_custom_parameters()
    run_state = store.read_run_state().as_dict() if store.run_state_path.exists() else None
    return {
        "additional_prompt": store.read_additional_prompt(),
        "agent_identity": store.read_agent_identity(),
        "custom_parameters": custom_parameters,
        "email_count": len(lead_database.emails),
        "icp_profiles": resolve_instagram_icp_profiles(store.read_icp_profiles(), custom_parameters),
        "lead_count": len(lead_database.leads),
        "memory_path": str(store.memory_path.resolve()),
        "recent_searches": [record.as_dict() for record in search_history[-5:]],
        "recent_searches_by_icp": store.read_recent_searches_by_icp(5),
        "run_state": run_state,
        "runtime_parameters": store.read_runtime_parameters(),
        "search_count": len(search_history),
    }


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


__all__ = [
    "SUPPORTED_INSTAGRAM_CUSTOM_PARAMETERS",
    "SUPPORTED_INSTAGRAM_RUNTIME_PARAMETERS",
    "normalize_instagram_custom_parameters",
    "normalize_instagram_runtime_parameters",
    "register_instagram_commands",
]
