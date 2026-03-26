"""CLI commands for the Google Maps prospecting agent."""

from __future__ import annotations

import argparse
import importlib
import os
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from harnessiq.agents import GoogleMapsProspectingAgent, ProspectingMemoryStore
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
from harnessiq.shared.prospecting import (
    PROSPECTING_HARNESS_MANIFEST,
    SUPPORTED_PROSPECTING_CUSTOM_PARAMETERS,
    SUPPORTED_PROSPECTING_RUNTIME_PARAMETERS,
    normalize_prospecting_custom_parameters,
    normalize_prospecting_runtime_parameters,
    slugify_agent_name,
    validate_company_description_for_run,
)

_DEFAULT_BROWSER_TOOLS_FACTORY = "harnessiq.integrations.google_maps_playwright:create_browser_tools"


def register_prospecting_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser("prospecting", help="Manage and run the Google Maps prospecting agent")
    parser.set_defaults(command_handler=lambda args: _print_help(parser))
    prospecting_subparsers = parser.add_subparsers(dest="prospecting_command")

    prepare_parser = prospecting_subparsers.add_parser(
        "prepare",
        help="Create or refresh a Google Maps prospecting memory folder",
    )
    add_agent_options(
        prepare_parser,
        agent_help="Logical agent name used to resolve the memory folder.",
        memory_root_default="memory/prospecting",
        memory_root_help="Root directory that holds per-agent prospecting memory folders.",
    )
    prepare_parser.set_defaults(command_handler=_handle_prepare)

    configure_parser = prospecting_subparsers.add_parser(
        "configure",
        help="Persist company description, prompts, and parameters for the prospecting agent",
    )
    add_agent_options(
        configure_parser,
        agent_help="Logical agent name used to resolve the memory folder.",
        memory_root_default="memory/prospecting",
        memory_root_help="Root directory that holds per-agent prospecting memory folders.",
    )
    add_text_or_file_options(configure_parser, "company_description", "Company description")
    add_text_or_file_options(configure_parser, "agent_identity", "Agent identity")
    add_text_or_file_options(configure_parser, "additional_prompt", "Additional prompt")
    configure_parser.add_argument(
        "--eval-system-prompt-file",
        help="Path to a UTF-8 text file that replaces the default company evaluation prompt.",
    )
    configure_parser.add_argument(
        "--runtime-param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help=(
            "Persist a prospecting runtime parameter. Supported keys: "
            f"{format_manifest_parameter_keys(PROSPECTING_HARNESS_MANIFEST, scope='runtime')}."
        ),
    )
    configure_parser.add_argument(
        "--custom-param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help=(
            "Persist a prospecting custom parameter. Supported keys: "
            f"{format_manifest_parameter_keys(PROSPECTING_HARNESS_MANIFEST, scope='custom')}."
        ),
    )
    configure_parser.set_defaults(command_handler=_handle_configure)

    show_parser = prospecting_subparsers.add_parser(
        "show",
        help="Render the current prospecting agent state as JSON",
    )
    add_agent_options(
        show_parser,
        agent_help="Logical agent name used to resolve the memory folder.",
        memory_root_default="memory/prospecting",
        memory_root_help="Root directory that holds per-agent prospecting memory folders.",
    )
    show_parser.set_defaults(command_handler=_handle_show)

    run_parser = prospecting_subparsers.add_parser(
        "run",
        help="Run the Google Maps prospecting agent from persisted memory",
    )
    add_agent_options(
        run_parser,
        agent_help="Logical agent name used to resolve the memory folder.",
        memory_root_default="memory/prospecting",
        memory_root_help="Root directory that holds per-agent prospecting memory folders.",
    )
    add_model_selection_options(run_parser)
    run_parser.add_argument(
        "--browser-tools-factory",
        default=_DEFAULT_BROWSER_TOOLS_FACTORY,
        help=(
            "Import path in the form module:callable that returns an iterable of browser tools. "
            f"Defaults to {_DEFAULT_BROWSER_TOOLS_FACTORY}."
        ),
    )
    run_parser.add_argument(
        "--runtime-param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Override a persisted prospecting runtime parameter for this run only.",
    )
    run_parser.add_argument(
        "--custom-param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Override a persisted prospecting custom parameter for this run only.",
    )
    run_parser.add_argument(
        "--sink",
        action="append",
        default=[],
        metavar="SPEC",
        help="Add a per-run output sink override using kind:value or kind:key=value,key=value.",
    )
    run_parser.add_argument("--max-cycles", type=int, help="Optional max cycle count passed to agent.run().")
    add_policy_options(run_parser)
    run_parser.set_defaults(command_handler=_handle_run)

    init_browser_parser = prospecting_subparsers.add_parser(
        "init-browser",
        help="Open a persistent browser session and save it for Google Maps prospecting runs",
    )
    add_agent_options(
        init_browser_parser,
        agent_help="Logical agent name used to resolve the memory folder.",
        memory_root_default="memory/prospecting",
        memory_root_help="Root directory that holds per-agent prospecting memory folders.",
    )
    init_browser_parser.add_argument(
        "--channel",
        default="chrome",
        help="Browser channel to use (default: chrome).",
    )
    init_browser_parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Launch headless instead of opening a visible browser window.",
    )
    init_browser_parser.set_defaults(command_handler=_handle_init_browser)


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

    company_description = resolve_text_argument(args.company_description_text, args.company_description_file)
    if company_description is not None:
        store.write_company_description(company_description)
        store.ensure_state_matches_company_description()
        updated.append("company_description")

    agent_identity = resolve_text_argument(args.agent_identity_text, args.agent_identity_file)
    if agent_identity is not None:
        store.write_agent_identity(agent_identity)
        updated.append("agent_identity")

    additional_prompt = resolve_text_argument(args.additional_prompt_text, args.additional_prompt_file)
    if additional_prompt is not None:
        store.write_additional_prompt(additional_prompt)
        updated.append("additional_prompt")

    runtime_parameters = store.read_runtime_parameters()
    runtime_parameters.update(_parse_runtime_assignments(args.runtime_param))
    if args.runtime_param:
        store.write_runtime_parameters(runtime_parameters)
        updated.append("runtime_parameters")

    custom_parameters = store.read_custom_parameters()
    custom_parameters.update(_parse_custom_assignments(args.custom_param))
    if args.eval_system_prompt_file:
        custom_parameters["eval_system_prompt"] = Path(args.eval_system_prompt_file).read_text(encoding="utf-8")
        updated.append("eval_system_prompt")
    if args.custom_param or args.eval_system_prompt_file:
        store.write_custom_parameters(custom_parameters)
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
    store = _load_store(args)
    store.prepare()
    validate_company_description_for_run(store.read_company_description())
    seed_cli_environment(Path(args.memory_root).expanduser())

    if "HARNESSIQ_PROSPECTING_SESSION_DIR" not in os.environ:
        os.environ["HARNESSIQ_PROSPECTING_SESSION_DIR"] = str(store.browser_data_dir.resolve())

    model = resolve_agent_model_from_args(args)

    created_tools = _load_factory(args.browser_tools_factory)()
    if created_tools is None:
        browser_tools: Iterable[Any] = ()
    elif isinstance(created_tools, (str, bytes)):
        raise TypeError("Browser tools factory must return an iterable of tool objects, not a string.")
    else:
        browser_tools = tuple(created_tools)

    runtime_config = build_runtime_config(
        sink_specs=args.sink,
        approval_policy=args.approval_policy,
        allowed_tools=args.allowed_tools,
    )
    agent = GoogleMapsProspectingAgent.from_memory(
        model=model,
        memory_path=store.memory_path,
        browser_tools=tuple(browser_tools),
        runtime_overrides=_parse_runtime_assignments(args.runtime_param),
        custom_overrides=_parse_custom_assignments(args.custom_param),
        runtime_config=runtime_config,
    )
    result = agent.run(max_cycles=args.max_cycles)
    payload = _build_summary(store)
    payload.update(
        {
            "agent": args.agent,
            "ledger_run_id": agent.last_run_id,
            "result": {
                "cycles_completed": result.cycles_completed,
                "pause_reason": result.pause_reason,
                "resets": result.resets,
                "status": result.status,
            },
        }
    )
    emit_json(payload)
    return 0


def _handle_init_browser(args: argparse.Namespace) -> int:
    try:
        from harnessiq.integrations.google_maps_playwright import PlaywrightGoogleMapsSession
    except ImportError as exc:
        raise RuntimeError(
            "playwright is required. Install with: pip install playwright && python -m playwright install chromium"
        ) from exc

    store = _load_store(args)
    store.prepare()
    session = PlaywrightGoogleMapsSession(
        session_dir=store.browser_data_dir,
        channel=args.channel,
        headless=bool(args.headless),
    )
    session.start()

    print(f"Browser session saved to: {store.browser_data_dir.resolve()}")
    print()
    print("Open Google Maps, sign in if needed, then press Enter to close the browser.")
    input()
    session.stop()
    emit_json(
        {
            "agent": args.agent,
            "browser_data_dir": str(store.browser_data_dir.resolve()),
            "status": "session_saved",
        }
    )
    return 0


def _load_store(args: argparse.Namespace) -> ProspectingMemoryStore:
    return ProspectingMemoryStore(
        memory_path=resolve_memory_path(args.agent, args.memory_root, slugifier=slugify_agent_name)
    )


def _parse_runtime_assignments(assignments: Sequence[str]) -> dict[str, Any]:
    return parse_manifest_parameter_assignments(
        assignments,
        manifest=PROSPECTING_HARNESS_MANIFEST,
        scope="runtime",
    )


def _parse_custom_assignments(assignments: Sequence[str]) -> dict[str, Any]:
    return parse_manifest_parameter_assignments(
        assignments,
        manifest=PROSPECTING_HARNESS_MANIFEST,
        scope="custom",
    )


def _build_summary(store: ProspectingMemoryStore) -> dict[str, Any]:
    state = store.read_state()
    qualified_leads = store.read_qualified_leads()
    return {
        "additional_prompt": store.read_additional_prompt(),
        "agent_identity": store.read_agent_identity(),
        "company_description": store.read_company_description(),
        "custom_parameters": store.read_custom_parameters(),
        "memory_path": str(store.memory_path.resolve()),
        "qualified_lead_count": len(qualified_leads),
        "recent_qualified_leads": [record.as_dict() for record in qualified_leads[-5:]],
        "run_state": state.as_dict(),
        "runtime_parameters": store.read_runtime_parameters(),
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
    "SUPPORTED_PROSPECTING_CUSTOM_PARAMETERS",
    "SUPPORTED_PROSPECTING_RUNTIME_PARAMETERS",
    "normalize_prospecting_custom_parameters",
    "normalize_prospecting_runtime_parameters",
    "register_prospecting_commands",
]
