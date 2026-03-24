"""CLI commands for the ResearchSweepAgent harness."""

from __future__ import annotations

import argparse
import importlib
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from harnessiq.agents import AgentRuntimeConfig, ResearchSweepAgent
from harnessiq.cli._langsmith import seed_cli_environment
from harnessiq.cli.common import (
    add_agent_options,
    add_text_or_file_options,
    emit_json,
    format_manifest_parameter_keys,
    parse_manifest_parameter_assignments,
    resolve_memory_path,
    resolve_repo_root,
    resolve_text_argument,
)
from harnessiq.config import (
    AgentCredentialsNotConfiguredError,
    CredentialsConfigStore,
    HarnessProfile,
    get_provider_credential_spec,
)
from harnessiq.shared.research_sweep import (
    RESEARCH_SWEEP_HARNESS_MANIFEST,
    ResearchSweepMemoryStore,
    normalize_research_sweep_custom_parameters,
    normalize_research_sweep_runtime_parameters,
    validate_query_for_run,
)
from harnessiq.utils import ConnectionsConfigStore, build_output_sinks

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
    reset_required = False

    custom_parameters = store.read_custom_parameters()
    runtime_parameters = store.read_runtime_parameters()

    query = resolve_text_argument(
        getattr(args, "query_text", None),
        getattr(args, "query_file", None),
    )
    if query is not None:
        normalized_query = validate_query_for_run(query)
        store.write_query(normalized_query)
        custom_parameters["query"] = normalized_query
        updated.append("query")
        reset_required = True

    additional_prompt = resolve_text_argument(
        getattr(args, "additional_prompt_text", None),
        getattr(args, "additional_prompt_file", None),
    )
    if additional_prompt is not None:
        store.write_additional_prompt(additional_prompt)
        updated.append("additional_prompt")
        reset_required = True

    parsed_runtime = _parse_runtime_assignments(args.runtime_param)
    if parsed_runtime:
        runtime_parameters.update(parsed_runtime)
        store.write_runtime_parameters(runtime_parameters)
        updated.append("runtime_parameters")

    parsed_custom = _parse_custom_assignments(args.custom_param)
    if parsed_custom:
        custom_parameters.update(parsed_custom)
        if "query" in parsed_custom:
            store.write_query(validate_query_for_run(str(parsed_custom["query"])))
            reset_required = True
        if "allowed_serper_operations" in parsed_custom:
            reset_required = True
        store.write_custom_parameters(custom_parameters)
        updated.append("custom_parameters")
    else:
        store.write_custom_parameters(custom_parameters)

    if reset_required:
        store.clear_context_runtime_state()
        updated.append("progress_reset")

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
    query = validate_query_for_run(store.read_query())
    seed_cli_environment(Path(args.memory_root).expanduser())

    model = _load_factory(args.model_factory)()
    if not hasattr(model, "generate_turn"):
        raise TypeError("Model factory must return an object that implements generate_turn(request).")

    serper_credentials = _resolve_serper_credentials(args)
    runtime_overrides = _parse_runtime_assignments(args.runtime_param)
    custom_overrides = _parse_custom_assignments(args.custom_param)
    custom_overrides["query"] = str(custom_overrides.get("query") or query)
    runtime_config = _build_runtime_config(args.sink)
    agent = ResearchSweepAgent.from_memory(
        model=model,
        memory_path=store.memory_path,
        serper_credentials=serper_credentials,
        runtime_overrides=runtime_overrides,
        custom_overrides=custom_overrides,
        runtime_config=runtime_config,
        instance_name=args.agent,
    )
    result = agent.run(max_cycles=args.max_cycles)
    payload = _build_summary(store)
    payload.update(
        {
            "agent": args.agent,
            "instance_id": getattr(agent, "instance_id", None),
            "instance_name": getattr(agent, "instance_name", None),
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


def _load_store(args: argparse.Namespace) -> ResearchSweepMemoryStore:
    return ResearchSweepMemoryStore(memory_path=resolve_memory_path(args.agent, args.memory_root))


def _parse_runtime_assignments(assignments: Sequence[str]) -> dict[str, Any]:
    return parse_manifest_parameter_assignments(
        assignments,
        manifest=RESEARCH_SWEEP_HARNESS_MANIFEST,
        scope="runtime",
    )


def _parse_custom_assignments(assignments: Sequence[str]) -> dict[str, Any]:
    return parse_manifest_parameter_assignments(
        assignments,
        manifest=RESEARCH_SWEEP_HARNESS_MANIFEST,
        scope="custom",
    )


def _build_summary(store: ResearchSweepMemoryStore) -> dict[str, Any]:
    return {
        "additional_prompt": store.read_additional_prompt(),
        "custom_parameters": store.read_custom_parameters(),
        "final_report": store.read_final_report(),
        "memory_path": str(store.memory_path.resolve()),
        "query": store.read_query(),
        "research_memory": store.read_research_memory(),
        "research_memory_summary": store.read_research_memory_summary(),
        "runtime_parameters": store.read_runtime_parameters(),
    }


def _resolve_serper_credentials(args: argparse.Namespace):
    if args.serper_credentials_factory:
        return _load_factory(args.serper_credentials_factory)()

    repo_root = resolve_repo_root(args.memory_root)
    store = CredentialsConfigStore(repo_root=repo_root)
    binding_name = HarnessProfile(
        manifest_id=RESEARCH_SWEEP_HARNESS_MANIFEST.manifest_id,
        agent_name=args.agent,
    ).credential_binding_name
    try:
        binding = store.load().binding_for(binding_name)
    except AgentCredentialsNotConfiguredError as exc:
        raise ValueError(
            "--serper-credentials-factory is required unless you have already bound Serper credentials with "
            "`harnessiq credentials bind research_sweep ...`."
        ) from exc
    resolved = store.resolve_binding(binding)
    family_values = {
        field_name.partition(".")[2]: value
        for field_name, value in resolved.as_dict().items()
        if field_name.startswith("serper.")
    }
    return get_provider_credential_spec("serper").build_credentials(family_values)


def _build_runtime_config(sink_specs: Sequence[str]) -> AgentRuntimeConfig:
    if not sink_specs:
        return AgentRuntimeConfig()
    connections = ConnectionsConfigStore().load().enabled_connections()
    return AgentRuntimeConfig(
        output_sinks=build_output_sinks(connections=connections, sink_specs=sink_specs),
    )


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
    "SUPPORTED_RESEARCH_SWEEP_CUSTOM_PARAMETERS",
    "SUPPORTED_RESEARCH_SWEEP_RUNTIME_PARAMETERS",
    "normalize_research_sweep_custom_parameters",
    "normalize_research_sweep_runtime_parameters",
    "register_research_sweep_commands",
]
