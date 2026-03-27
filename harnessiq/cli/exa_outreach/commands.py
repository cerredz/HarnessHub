"""ExaOutreach CLI commands for managed memory and agent execution."""

from __future__ import annotations

import argparse

from harnessiq.cli.builders import ExaOutreachCliBuilder
from harnessiq.cli.common import (
    add_agent_options,
    add_policy_options,
    add_model_selection_options,
    add_text_or_file_options,
    emit_json,
    format_manifest_parameter_keys,
)
from harnessiq.cli.runners import ExaOutreachCliRunner
from harnessiq.shared.exa_outreach import EXA_OUTREACH_HARNESS_MANIFEST

SUPPORTED_EXA_OUTREACH_RUNTIME_PARAMETERS = EXA_OUTREACH_HARNESS_MANIFEST.runtime_parameter_names


def register_exa_outreach_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser("outreach", help="Manage and run the ExaOutreach agent")
    parser.set_defaults(command_handler=lambda args: _print_help(parser))
    outreach_subparsers = parser.add_subparsers(dest="outreach_command")

    prepare_parser = outreach_subparsers.add_parser(
        "prepare", help="Create or refresh an outreach agent memory folder"
    )
    add_agent_options(
        prepare_parser,
        agent_help="Logical agent name used to resolve the memory folder.",
        memory_root_default="memory/outreach",
        memory_root_help="Root directory that holds per-agent outreach memory folders.",
    )
    prepare_parser.set_defaults(command_handler=_handle_prepare)

    configure_parser = outreach_subparsers.add_parser(
        "configure",
        help="Write outreach agent search query, identity, runtime params, and additional prompt",
    )
    add_agent_options(
        configure_parser,
        agent_help="Logical agent name used to resolve the memory folder.",
        memory_root_default="memory/outreach",
        memory_root_help="Root directory that holds per-agent outreach memory folders.",
    )
    add_text_or_file_options(configure_parser, "query", "Search query")
    add_text_or_file_options(configure_parser, "agent_identity", "Agent identity")
    add_text_or_file_options(configure_parser, "additional_prompt", "Additional prompt")
    configure_parser.add_argument(
        "--runtime-param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help=(
            f"Persist a runtime parameter. Supported keys: "
            f"{format_manifest_parameter_keys(EXA_OUTREACH_HARNESS_MANIFEST, scope='runtime')}."
        ),
    )
    configure_parser.set_defaults(command_handler=_handle_configure)

    show_parser = outreach_subparsers.add_parser(
        "show", help="Render the current outreach agent state as JSON"
    )
    add_agent_options(
        show_parser,
        agent_help="Logical agent name used to resolve the memory folder.",
        memory_root_default="memory/outreach",
        memory_root_help="Root directory that holds per-agent outreach memory folders.",
    )
    show_parser.set_defaults(command_handler=_handle_show)

    run_parser = outreach_subparsers.add_parser(
        "run", help="Run the ExaOutreach agent from persisted CLI state"
    )
    add_agent_options(
        run_parser,
        agent_help="Logical agent name used to resolve the memory folder.",
        memory_root_default="memory/outreach",
        memory_root_help="Root directory that holds per-agent outreach memory folders.",
    )
    add_model_selection_options(run_parser)
    run_parser.add_argument(
        "--exa-credentials-factory",
        required=True,
        help="Import path (module:callable) that returns an ExaCredentials instance.",
    )
    run_parser.add_argument(
        "--resend-credentials-factory",
        default=None,
        help="Import path (module:callable) that returns a ResendCredentials instance. Required unless --search-only.",
    )
    run_parser.add_argument(
        "--email-data-factory",
        default=None,
        help="Import path (module:callable) that returns a list[dict] of email templates. Required unless --search-only.",
    )
    run_parser.add_argument(
        "--search-only",
        action="store_true",
        default=False,
        help="Discover and log leads only — skip template selection and email sending.",
    )
    run_parser.add_argument(
        "--runtime-param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Override a persisted runtime parameter for this run only.",
    )
    run_parser.add_argument(
        "--sink",
        action="append",
        default=[],
        metavar="SPEC",
        help="Add a per-run output sink override using kind:value or kind:key=value,key=value.",
    )
    run_parser.add_argument(
        "--max-cycles", type=int, help="Optional max cycle count passed to agent.run()."
    )
    add_policy_options(run_parser)
    run_parser.set_defaults(command_handler=_handle_run)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def _handle_prepare(args: argparse.Namespace) -> int:
    emit_json(
        ExaOutreachCliBuilder().prepare(
            agent_name=args.agent,
            memory_root=args.memory_root,
        )
    )
    return 0


def _handle_configure(args: argparse.Namespace) -> int:
    emit_json(
        ExaOutreachCliBuilder().configure(
            agent_name=args.agent,
            memory_root=args.memory_root,
            query_text=getattr(args, "query_text", None),
            query_file=getattr(args, "query_file", None),
            agent_identity_text=getattr(args, "agent_identity_text", None),
            agent_identity_file=getattr(args, "agent_identity_file", None),
            additional_prompt_text=getattr(args, "additional_prompt_text", None),
            additional_prompt_file=getattr(args, "additional_prompt_file", None),
            runtime_assignments=args.runtime_param,
        )
    )
    return 0


def _handle_show(args: argparse.Namespace) -> int:
    emit_json(
        ExaOutreachCliBuilder().show(
            agent_name=args.agent,
            memory_root=args.memory_root,
        )
    )
    return 0


def _handle_run(args: argparse.Namespace) -> int:
    emit_json(
        ExaOutreachCliRunner().run(
            agent_name=args.agent,
            memory_root=args.memory_root,
            model_factory=args.model_factory,
            model=args.model,
            model_profile=args.model_profile,
            exa_credentials_factory=args.exa_credentials_factory,
            resend_credentials_factory=args.resend_credentials_factory,
            email_data_factory=args.email_data_factory,
            search_only=bool(getattr(args, "search_only", False)),
            runtime_assignments=args.runtime_param,
            sink_specs=args.sink,
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


def _print_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 0


def normalize_exa_outreach_runtime_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    """Validate and type-coerce outreach runtime parameters."""
    return EXA_OUTREACH_HARNESS_MANIFEST.coerce_runtime_parameters(parameters)


__all__ = [
    "SUPPORTED_EXA_OUTREACH_RUNTIME_PARAMETERS",
    "normalize_exa_outreach_runtime_parameters",
    "register_exa_outreach_commands",
]
