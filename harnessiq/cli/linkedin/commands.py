"""LinkedIn CLI commands for managed memory and agent execution."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from harnessiq.cli.builders import LinkedInCliBuilder
from harnessiq.cli.common import (
    add_agent_options,
    add_policy_options,
    add_model_selection_options,
    add_text_or_file_options,
    emit_json,
    format_manifest_parameter_keys,
)
from harnessiq.cli.runners import LinkedInCliRunner
from harnessiq.agents.linkedin import LINKEDIN_HARNESS_MANIFEST


def register_linkedin_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("linkedin", help="Manage and run the LinkedIn agent")
    parser.set_defaults(command_handler=lambda args: _print_help(parser))
    linkedin_subparsers = parser.add_subparsers(dest="linkedin_command")

    prepare_parser = linkedin_subparsers.add_parser("prepare", help="Create or refresh a LinkedIn agent memory folder")
    add_agent_options(
        prepare_parser,
        agent_help="Logical LinkedIn agent name used to resolve the memory folder.",
        memory_root_default="memory/linkedin",
        memory_root_help="Root directory that holds per-agent LinkedIn memory folders.",
    )
    prepare_parser.set_defaults(command_handler=_handle_prepare)

    configure_parser = linkedin_subparsers.add_parser(
        "configure",
        help="Write LinkedIn memory inputs, custom parameters, and managed files",
    )
    add_agent_options(
        configure_parser,
        agent_help="Logical LinkedIn agent name used to resolve the memory folder.",
        memory_root_default="memory/linkedin",
        memory_root_help="Root directory that holds per-agent LinkedIn memory folders.",
    )
    add_text_or_file_options(configure_parser, "job_preferences", "Job preferences")
    add_text_or_file_options(configure_parser, "user_profile", "User profile")
    add_text_or_file_options(configure_parser, "agent_identity", "Agent identity")
    add_text_or_file_options(configure_parser, "additional_prompt", "Additional prompt")
    configure_parser.add_argument(
        "--runtime-param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help=(
            "Persist a LinkedIn runtime parameter. Supported keys: "
            f"{format_manifest_parameter_keys(LINKEDIN_HARNESS_MANIFEST, scope='runtime')}."
        ),
    )
    configure_parser.add_argument(
        "--custom-param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Persist a user-defined key/value pair. Values are parsed as JSON when possible.",
    )
    configure_parser.add_argument(
        "--import-file",
        action="append",
        default=[],
        metavar="PATH",
        help="Copy a file into managed LinkedIn memory storage while preserving its source path.",
    )
    configure_parser.add_argument(
        "--inline-file",
        action="append",
        default=[],
        metavar="NAME=CONTENT",
        help="Write a managed text file directly into LinkedIn memory storage.",
    )
    configure_parser.set_defaults(command_handler=_handle_configure)

    show_parser = linkedin_subparsers.add_parser("show", help="Render the current LinkedIn CLI-managed state as JSON")
    add_agent_options(
        show_parser,
        agent_help="Logical LinkedIn agent name used to resolve the memory folder.",
        memory_root_default="memory/linkedin",
        memory_root_help="Root directory that holds per-agent LinkedIn memory folders.",
    )
    show_parser.set_defaults(command_handler=_handle_show)

    run_parser = linkedin_subparsers.add_parser("run", help="Run the LinkedIn SDK agent from persisted CLI state")
    add_agent_options(
        run_parser,
        agent_help="Logical LinkedIn agent name used to resolve the memory folder.",
        memory_root_default="memory/linkedin",
        memory_root_help="Root directory that holds per-agent LinkedIn memory folders.",
    )
    add_model_selection_options(run_parser)
    run_parser.add_argument(
        "--browser-tools-factory",
        help="Optional import path in the form module:callable that returns an iterable of browser tools.",
    )
    run_parser.add_argument(
        "--runtime-param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Override a persisted LinkedIn runtime parameter for this run only.",
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

    init_browser_parser = linkedin_subparsers.add_parser(
        "init-browser",
        help="Open a browser, wait for LinkedIn login, and save the session for future runs",
    )
    add_agent_options(
        init_browser_parser,
        agent_help="Logical LinkedIn agent name used to resolve the memory folder.",
        memory_root_default="memory/linkedin",
        memory_root_help="Root directory that holds per-agent LinkedIn memory folders.",
    )
    init_browser_parser.set_defaults(command_handler=_handle_init_browser)


def _handle_prepare(args: argparse.Namespace) -> int:
    emit_json(
        LinkedInCliBuilder().prepare(
            agent_name=args.agent,
            memory_root=args.memory_root,
        )
    )
    return 0


def _handle_configure(args: argparse.Namespace) -> int:
    emit_json(
        LinkedInCliBuilder().configure(
            agent_name=args.agent,
            memory_root=args.memory_root,
            job_preferences_text=args.job_preferences_text,
            job_preferences_file=args.job_preferences_file,
            user_profile_text=args.user_profile_text,
            user_profile_file=args.user_profile_file,
            agent_identity_text=args.agent_identity_text,
            agent_identity_file=args.agent_identity_file,
            additional_prompt_text=args.additional_prompt_text,
            additional_prompt_file=args.additional_prompt_file,
            runtime_assignments=args.runtime_param,
            custom_assignments=args.custom_param,
            import_files=args.import_file,
            inline_files=args.inline_file,
        )
    )
    return 0


def _handle_show(args: argparse.Namespace) -> int:
    emit_json(
        LinkedInCliBuilder().show(
            agent_name=args.agent,
            memory_root=args.memory_root,
        )
    )
    return 0


def _handle_run(args: argparse.Namespace) -> int:
    emit_json(
        LinkedInCliRunner().run(
            agent_name=args.agent,
            memory_root=args.memory_root,
            model_factory=args.model_factory,
            model=args.model,
            model_profile=args.model_profile,
            browser_tools_factory=args.browser_tools_factory,
            runtime_assignments=args.runtime_param,
            sink_specs=args.sink,
            max_cycles=args.max_cycles,
            approval_policy=args.approval_policy,
            allowed_tools=args.allowed_tools,
        )
    )
    return 0


def _handle_init_browser(args: argparse.Namespace) -> int:
    emit_json(
        LinkedInCliRunner().init_browser(
            agent_name=args.agent,
            memory_root=args.memory_root,
        )
    )
    return 0


def _print_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 0


__all__ = ["register_linkedin_commands"]
