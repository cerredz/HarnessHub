"""CLI commands for the ResearchSweepAgent harness."""

from __future__ import annotations

import argparse

from harnessiq.cli.builders import ResearchSweepCliBuilder
from harnessiq.cli.common import (
    add_agent_options,
    add_text_or_file_options,
    emit_json,
    format_manifest_parameter_keys,
)
from harnessiq.cli.runners import ResearchSweepCliRunner
from harnessiq.shared.research_sweep import (
    RESEARCH_SWEEP_HARNESS_MANIFEST,
    normalize_research_sweep_custom_parameters,
    normalize_research_sweep_runtime_parameters,
)

SUPPORTED_RESEARCH_SWEEP_RUNTIME_PARAMETERS = RESEARCH_SWEEP_HARNESS_MANIFEST.runtime_parameter_names
SUPPORTED_RESEARCH_SWEEP_CUSTOM_PARAMETERS = RESEARCH_SWEEP_HARNESS_MANIFEST.custom_parameter_names


def register_research_sweep_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser("research-sweep", help="Manage and run the ResearchSweepAgent harness")
    parser.set_defaults(command_handler=lambda args: _print_help(parser))
    research_subparsers = parser.add_subparsers(dest="research_sweep_command")

    prepare_parser = research_subparsers.add_parser(
        "prepare",
        help="Create or refresh a research sweep memory folder",
    )
    add_agent_options(
        prepare_parser,
        agent_help="Logical agent name used to resolve the memory folder.",
        memory_root_default="memory/research_sweep",
        memory_root_help="Root directory that holds per-agent research sweep memory folders.",
    )
    prepare_parser.set_defaults(command_handler=_handle_prepare)

    configure_parser = research_subparsers.add_parser(
        "configure",
        help="Persist the research query, prompt text, and parameters for the research sweep harness",
    )
    add_agent_options(
        configure_parser,
        agent_help="Logical agent name used to resolve the memory folder.",
        memory_root_default="memory/research_sweep",
        memory_root_help="Root directory that holds per-agent research sweep memory folders.",
    )
    add_text_or_file_options(configure_parser, "query", "Research query")
    add_text_or_file_options(configure_parser, "additional_prompt", "Additional prompt")
    configure_parser.add_argument(
        "--runtime-param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help=(
            "Persist a research sweep runtime parameter. Supported keys: "
            f"{format_manifest_parameter_keys(RESEARCH_SWEEP_HARNESS_MANIFEST, scope='runtime')}."
        ),
    )
    configure_parser.add_argument(
        "--custom-param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help=(
            "Persist a research sweep custom parameter. Supported keys: "
            f"{format_manifest_parameter_keys(RESEARCH_SWEEP_HARNESS_MANIFEST, scope='custom')}."
        ),
    )
    configure_parser.set_defaults(command_handler=_handle_configure)

    show_parser = research_subparsers.add_parser(
        "show",
        help="Render the current research sweep harness state as JSON",
    )
    add_agent_options(
        show_parser,
        agent_help="Logical agent name used to resolve the memory folder.",
        memory_root_default="memory/research_sweep",
        memory_root_help="Root directory that holds per-agent research sweep memory folders.",
    )
    show_parser.set_defaults(command_handler=_handle_show)

    run_parser = research_subparsers.add_parser(
        "run",
        help="Run the ResearchSweepAgent from persisted memory",
    )
    add_agent_options(
        run_parser,
        agent_help="Logical agent name used to resolve the memory folder.",
        memory_root_default="memory/research_sweep",
        memory_root_help="Root directory that holds per-agent research sweep memory folders.",
    )
    run_parser.add_argument(
        "--model-factory",
        required=True,
        help="Import path in the form module:callable that returns an AgentModel instance.",
    )
    run_parser.add_argument(
        "--serper-credentials-factory",
        help="Optional import path (module:callable) that returns a SerperCredentials instance.",
    )
    run_parser.add_argument(
        "--runtime-param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Override a persisted research sweep runtime parameter for this run only.",
    )
    run_parser.add_argument(
        "--custom-param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Override a persisted research sweep custom parameter for this run only.",
    )
    run_parser.add_argument("--max-cycles", type=int, help="Optional max cycle count passed to agent.run().")
    run_parser.add_argument(
        "--sink",
        action="append",
        default=[],
        metavar="SPEC",
        help="Add a per-run output sink override using kind:value or kind:key=value,key=value.",
    )
    run_parser.set_defaults(command_handler=_handle_run)


def _handle_prepare(args: argparse.Namespace) -> int:
    emit_json(
        ResearchSweepCliBuilder().prepare(
            agent_name=args.agent,
            memory_root=args.memory_root,
        )
    )
    return 0


def _handle_configure(args: argparse.Namespace) -> int:
    emit_json(
        ResearchSweepCliBuilder().configure(
            agent_name=args.agent,
            memory_root=args.memory_root,
            query_text=getattr(args, "query_text", None),
            query_file=getattr(args, "query_file", None),
            additional_prompt_text=getattr(args, "additional_prompt_text", None),
            additional_prompt_file=getattr(args, "additional_prompt_file", None),
            runtime_assignments=args.runtime_param,
            custom_assignments=args.custom_param,
        )
    )
    return 0


def _handle_show(args: argparse.Namespace) -> int:
    emit_json(
        ResearchSweepCliBuilder().show(
            agent_name=args.agent,
            memory_root=args.memory_root,
        )
    )
    return 0


def _handle_run(args: argparse.Namespace) -> int:
    emit_json(
        ResearchSweepCliRunner().run(
            agent_name=args.agent,
            memory_root=args.memory_root,
            model_factory=args.model_factory,
            serper_credentials_factory=args.serper_credentials_factory,
            runtime_assignments=args.runtime_param,
            custom_assignments=args.custom_param,
            sink_specs=args.sink,
            max_cycles=args.max_cycles,
        )
    )
    return 0


def _print_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 0


__all__ = [
    "SUPPORTED_RESEARCH_SWEEP_CUSTOM_PARAMETERS",
    "SUPPORTED_RESEARCH_SWEEP_RUNTIME_PARAMETERS",
    "normalize_research_sweep_custom_parameters",
    "normalize_research_sweep_runtime_parameters",
    "register_research_sweep_commands",
]
