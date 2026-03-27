"""CLI commands for the Google Maps prospecting agent."""

from __future__ import annotations

import argparse

from harnessiq.cli.builders import ProspectingCliBuilder
from harnessiq.cli.common import (
    add_agent_options,
    add_policy_options,
    add_model_selection_options,
    add_text_or_file_options,
    emit_json,
    format_manifest_parameter_keys,
)
from harnessiq.cli.runners import ProspectingCliRunner
from harnessiq.shared.prospecting import (
    PROSPECTING_HARNESS_MANIFEST,
    SUPPORTED_PROSPECTING_CUSTOM_PARAMETERS,
    SUPPORTED_PROSPECTING_RUNTIME_PARAMETERS,
    normalize_prospecting_custom_parameters,
    normalize_prospecting_runtime_parameters,
)

from harnessiq.cli.runners.prospecting import _DEFAULT_BROWSER_TOOLS_FACTORY


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
    emit_json(
        ProspectingCliBuilder().prepare(
            agent_name=args.agent,
            memory_root=args.memory_root,
        )
    )
    return 0


def _handle_configure(args: argparse.Namespace) -> int:
    emit_json(
        ProspectingCliBuilder().configure(
            agent_name=args.agent,
            memory_root=args.memory_root,
            company_description_text=getattr(args, "company_description_text", None),
            company_description_file=getattr(args, "company_description_file", None),
            agent_identity_text=getattr(args, "agent_identity_text", None),
            agent_identity_file=getattr(args, "agent_identity_file", None),
            additional_prompt_text=getattr(args, "additional_prompt_text", None),
            additional_prompt_file=getattr(args, "additional_prompt_file", None),
            eval_system_prompt_file=args.eval_system_prompt_file,
            runtime_assignments=args.runtime_param,
            custom_assignments=args.custom_param,
        )
    )
    return 0


def _handle_show(args: argparse.Namespace) -> int:
    emit_json(
        ProspectingCliBuilder().show(
            agent_name=args.agent,
            memory_root=args.memory_root,
        )
    )
    return 0


def _handle_run(args: argparse.Namespace) -> int:
    emit_json(
        ProspectingCliRunner().run(
            agent_name=args.agent,
            memory_root=args.memory_root,
            model_factory=args.model_factory,
            model=args.model,
            model_profile=args.model_profile,
            browser_tools_factory=args.browser_tools_factory,
            runtime_assignments=args.runtime_param,
            custom_assignments=args.custom_param,
            sink_specs=args.sink,
            max_cycles=args.max_cycles,
            approval_policy=args.approval_policy,
            allowed_tools=args.allowed_tools,
        )
    )
    return 0


def _handle_init_browser(args: argparse.Namespace) -> int:
    emit_json(
        ProspectingCliRunner().init_browser(
            agent_name=args.agent,
            memory_root=args.memory_root,
            channel=args.channel,
            headless=bool(args.headless),
        )
    )
    return 0


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
