"""ExaOutreach CLI commands for managed memory and agent execution."""

from __future__ import annotations

import argparse
import importlib
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from harnessiq.cli.common import (
    add_agent_options,
    add_text_or_file_options,
    emit_json,
    format_manifest_parameter_keys,
    parse_manifest_parameter_assignments,
    resolve_memory_path,
    resolve_text_argument,
)
from harnessiq.cli._langsmith import seed_cli_environment
from harnessiq.agents import AgentRuntimeConfig
from harnessiq.shared.exa_outreach import EXA_OUTREACH_HARNESS_MANIFEST, ExaOutreachMemoryStore
from harnessiq.utils import ConnectionsConfigStore, build_output_sinks

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
    run_parser.add_argument(
        "--model-factory",
        required=True,
        help="Import path (module:callable) that returns an AgentModel instance.",
    )
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
    run_parser.set_defaults(command_handler=_handle_run)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


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

    query = resolve_text_argument(
        getattr(args, "query_text", None),
        getattr(args, "query_file", None),
    )
    if query is not None:
        config = store.read_query_config()
        config["search_query"] = query
        store.write_query_config(config)
        updated.append("search_query")

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

    runtime_params = _parse_runtime_assignments(args.runtime_param)
    if runtime_params:
        config = store.read_query_config()
        config.update(runtime_params)
        store.write_query_config(config)
        updated.append("runtime_parameters")

    payload = _build_summary(store)
    payload["updated"] = updated
    payload["status"] = "configured"
    emit_json(payload)
    return 0


def _handle_show(args: argparse.Namespace) -> int:
    store = _load_store(args)
    store.prepare()
    emit_json(_build_summary(store))
    return 0


def _handle_run(args: argparse.Namespace) -> int:
    from harnessiq.agents.exa_outreach import ExaOutreachAgent
    from harnessiq.shared.exa_outreach import EmailTemplate

    store = _load_store(args)
    store.prepare()
    seed_cli_environment(Path(args.memory_root).expanduser())

    search_only: bool = getattr(args, "search_only", False)

    if not search_only:
        if not args.resend_credentials_factory:
            raise ValueError("--resend-credentials-factory is required unless --search-only is set.")
        if not args.email_data_factory:
            raise ValueError("--email-data-factory is required unless --search-only is set.")

    model = _load_factory(args.model_factory)()
    if not hasattr(model, "generate_turn"):
        raise TypeError("Model factory must return an object that implements generate_turn(request).")

    exa_credentials = _load_factory(args.exa_credentials_factory)()
    resend_credentials = _load_factory(args.resend_credentials_factory)() if not search_only else None
    if not search_only:
        raw_email_data = _load_factory(args.email_data_factory)()
        if not isinstance(raw_email_data, list):
            raise TypeError("Email data factory must return a list of dicts.")
        email_data = [EmailTemplate.from_dict(d) for d in raw_email_data]
    else:
        email_data = []

    # Read persisted search query and runtime overrides
    query_config = store.read_query_config()
    runtime_overrides = _parse_runtime_assignments(args.runtime_param)
    query_config.update(runtime_overrides)

    search_query = str(query_config.pop("search_query", ""))
    max_tokens = int(query_config.pop("max_tokens", 80_000))
    reset_threshold = float(query_config.pop("reset_threshold", 0.9))

    agent = ExaOutreachAgent(
        model=model,
        exa_credentials=exa_credentials,
        resend_credentials=resend_credentials,
        email_data=email_data,
        search_only=search_only,
        search_query=search_query,
        memory_path=store.memory_path,
        max_tokens=max_tokens,
        reset_threshold=reset_threshold,
        runtime_config=_build_runtime_config(args.sink),
    )
    result = agent.run(max_cycles=args.max_cycles)

    # Print a run summary to stdout.
    run_id = agent._current_run_id or "unknown"
    if not isinstance(run_id, str):
        run_id = str(run_id)
    _print_run_summary(store, run_id)
    ledger_run_id = agent.last_run_id
    if ledger_run_id is not None and not isinstance(ledger_run_id, str):
        ledger_run_id = str(ledger_run_id)

    emit_json(
        {
            "agent": args.agent,
            "instance_id": _optional_string(getattr(agent, "instance_id", None)),
            "instance_name": _optional_string(getattr(agent, "instance_name", None)),
            "ledger_run_id": ledger_run_id,
            "memory_path": str(store.memory_path.resolve()),
            "run_id": run_id,
            "result": {
                "cycles_completed": result.cycles_completed,
                "pause_reason": result.pause_reason,
                "resets": result.resets,
                "status": result.status,
            },
        }
    )
    return 0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_store(args: argparse.Namespace) -> ExaOutreachMemoryStore:
    return ExaOutreachMemoryStore(memory_path=resolve_memory_path(args.agent, args.memory_root))


def _parse_runtime_assignments(assignments: Sequence[str]) -> dict[str, Any]:
    return parse_manifest_parameter_assignments(
        assignments,
        manifest=EXA_OUTREACH_HARNESS_MANIFEST,
        scope="runtime",
    )


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _build_summary(store: ExaOutreachMemoryStore) -> dict[str, Any]:
    return {
        "agent_identity": store.read_agent_identity(),
        "additional_prompt": store.read_additional_prompt(),
        "memory_path": str(store.memory_path.resolve()),
        "query_config": store.read_query_config(),
        "run_files": [str(p.name) for p in store.list_run_files()],
    }


def _load_factory(spec: str):
    module_name, separator, attribute_path = spec.partition(":")
    if not separator or not module_name or not attribute_path:
        raise ValueError(
            f"Factory import paths must use the form module:callable. Received '{spec}'."
        )
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


def _print_run_summary(store: ExaOutreachMemoryStore, run_id: str) -> None:
    print()
    print("=" * 64)
    try:
        run_log = store.read_run(run_id)
        print(f"  RUN {run_id.upper()}")
        print(f"  Leads found:  {len(run_log.leads_found)}")
        print(f"  Emails sent:  {len(run_log.emails_sent)}")
        if run_log.emails_sent:
            print("  " + "-" * 60)
            for record in run_log.emails_sent:
                print(f"  -> {record.to_name} <{record.to_email}> | {record.subject}")
    except FileNotFoundError:
        print(f"  No run file found for {run_id}.")
    print()
    print(f"  Run files saved to: {store.runs_dir.resolve()}")
    print("=" * 64)
    print()


def _build_runtime_config(sink_specs: Sequence[str]) -> AgentRuntimeConfig:
    if not sink_specs:
        return AgentRuntimeConfig()
    connections = ConnectionsConfigStore().load().enabled_connections()
    return AgentRuntimeConfig(
        output_sinks=build_output_sinks(connections=connections, sink_specs=sink_specs),
    )


def normalize_exa_outreach_runtime_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    """Validate and type-coerce outreach runtime parameters."""
    return EXA_OUTREACH_HARNESS_MANIFEST.coerce_runtime_parameters(parameters)


__all__ = [
    "SUPPORTED_EXA_OUTREACH_RUNTIME_PARAMETERS",
    "normalize_exa_outreach_runtime_parameters",
    "register_exa_outreach_commands",
]
