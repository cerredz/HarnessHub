"""Leads agent CLI commands for managed configuration and execution."""

from __future__ import annotations

import argparse
from typing import Any

from harnessiq.cli.builders import LeadsCliBuilder
from harnessiq.cli.common import (
    add_agent_options,
    add_policy_options,
    add_model_selection_options,
    add_text_or_file_options,
    emit_json,
    format_manifest_parameter_keys,
)
from harnessiq.cli.runners import LeadsCliRunner
from harnessiq.shared.leads import (
    LEADS_HARNESS_MANIFEST,
)

SUPPORTED_LEADS_RUNTIME_PARAMETERS = LEADS_HARNESS_MANIFEST.runtime_parameter_names


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
    add_policy_options(run_parser)
    run_parser.set_defaults(command_handler=_handle_run)


def _handle_prepare(args: argparse.Namespace) -> int:
    emit_json(
        LeadsCliBuilder().prepare(
            agent_name=args.agent,
            memory_root=args.memory_root,
        )
    )
    return 0


def _handle_configure(args: argparse.Namespace) -> int:
    emit_json(
        LeadsCliBuilder().configure(
            agent_name=args.agent,
            memory_root=args.memory_root,
            company_background_text=getattr(args, "company_background_text", None),
            company_background_file=getattr(args, "company_background_file", None),
            icp_texts=args.icp_text,
            icp_files=args.icp_file,
            platforms=args.platform,
            runtime_assignments=args.runtime_param,
        )
    )
    return 0


def _handle_show(args: argparse.Namespace) -> int:
    emit_json(
        LeadsCliBuilder().show(
            agent_name=args.agent,
            memory_root=args.memory_root,
        )
    )
    return 0


def _handle_run(args: argparse.Namespace) -> int:
    emit_json(
        LeadsCliRunner().run(
            agent_name=args.agent,
            memory_root=args.memory_root,
            model_factory=args.model_factory,
            model=args.model,
            model_profile=args.model_profile,
            provider_tools_factory=args.provider_tools_factory,
            provider_credentials_factories=args.provider_credentials_factory,
            provider_client_factories=args.provider_client_factory,
            storage_backend_factory=args.storage_backend_factory,
            runtime_assignments=args.runtime_param,
            max_cycles=args.max_cycles,
            approval_policy=args.approval_policy,
            allowed_tools=args.allowed_tools,
        )
    )
    return 0


def _print_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 0


def normalize_leads_runtime_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    return LEADS_HARNESS_MANIFEST.coerce_runtime_parameters(parameters)


__all__ = [
    "SUPPORTED_LEADS_RUNTIME_PARAMETERS",
    "normalize_leads_runtime_parameters",
    "register_leads_commands",
]
