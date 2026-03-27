"""CLI commands for the Instagram keyword discovery agent."""

from __future__ import annotations

import argparse

from harnessiq.cli.builders import InstagramCliBuilder
from harnessiq.cli.common import (
    add_agent_options,
    add_policy_options,
    add_model_selection_options,
    add_text_or_file_options,
    emit_json,
    format_manifest_parameter_keys,
)
from harnessiq.cli.runners import InstagramCliRunner
from harnessiq.shared.instagram import (
    INSTAGRAM_HARNESS_MANIFEST,
    normalize_instagram_custom_parameters,
    normalize_instagram_runtime_parameters,
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
    emit_json(
        InstagramCliBuilder().prepare(
            agent_name=args.agent,
            memory_root=args.memory_root,
        )
    )
    return 0


def _handle_configure(args: argparse.Namespace) -> int:
    emit_json(
        InstagramCliBuilder().configure(
            agent_name=args.agent,
            memory_root=args.memory_root,
            icp_values=args.icp,
            icp_file=args.icp_file,
            agent_identity_text=getattr(args, "agent_identity_text", None),
            agent_identity_file=getattr(args, "agent_identity_file", None),
            additional_prompt_text=getattr(args, "additional_prompt_text", None),
            additional_prompt_file=getattr(args, "additional_prompt_file", None),
            runtime_assignments=args.runtime_param,
            custom_assignments=args.custom_param,
        )
    )
    return 0


def _handle_show(args: argparse.Namespace) -> int:
    emit_json(
        InstagramCliBuilder().show(
            agent_name=args.agent,
            memory_root=args.memory_root,
        )
    )
    return 0


def _handle_run(args: argparse.Namespace) -> int:
    builder = InstagramCliBuilder()
    runner = InstagramCliRunner()
    custom_overrides = runner.parse_custom_assignments(args.custom_param)
    icp_profiles = builder.resolve_icp_profiles(
        icp_values=args.icp,
        icp_file=args.icp_file,
    )
    if icp_profiles is not None:
        custom_overrides["icp_profiles"] = icp_profiles
    emit_json(
        runner.run(
            agent_name=args.agent,
            memory_root=args.memory_root,
            model_factory=args.model_factory,
            model=args.model,
            model_profile=args.model_profile,
            search_backend_factory=args.search_backend_factory,
            runtime_overrides=runner.parse_runtime_assignments(args.runtime_param),
            custom_overrides=custom_overrides,
            max_cycles=args.max_cycles,
            approval_policy=args.approval_policy,
            allowed_tools=args.allowed_tools,
            dynamic_tools=args.dynamic_tools,
            dynamic_tool_candidates=args.dynamic_tool_candidates,
            dynamic_tool_top_k=args.dynamic_tool_top_k,
            dynamic_tool_embedding_model=args.dynamic_tool_embedding_model,
        )
    )
    return 0


def _handle_get_emails(args: argparse.Namespace) -> int:
    emit_json(
        InstagramCliBuilder().get_emails(
            agent_name=args.agent,
            memory_root=args.memory_root,
        )
    )
    return 0


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
