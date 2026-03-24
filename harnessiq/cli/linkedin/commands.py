"""LinkedIn CLI commands for managed memory and agent execution."""

from __future__ import annotations

import argparse
import importlib
import os
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from harnessiq.agents import LinkedInJobApplierAgent, LinkedInMemoryStore
from harnessiq.cli._langsmith import seed_cli_environment
from harnessiq.cli.common import (
    add_agent_options,
    add_text_or_file_options,
    emit_json,
    format_manifest_parameter_keys,
    parse_generic_assignments,
    parse_manifest_parameter_assignments,
    resolve_memory_path,
    resolve_text_argument,
    split_assignment,
)
from harnessiq.shared.agents import AgentRuntimeConfig
from harnessiq.agents.linkedin import (
    JobApplicationRecord,
    LINKEDIN_HARNESS_MANIFEST,
)
from harnessiq.utils import ConnectionsConfigStore, build_output_sinks


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
    run_parser.add_argument(
        "--model-factory",
        required=True,
        help="Import path in the form module:callable that returns an AgentModel instance.",
    )
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
    store = _load_store(args)
    store.prepare()
    emit_json({"agent": args.agent, "memory_path": str(store.memory_path.resolve()), "status": "prepared"})
    return 0


def _handle_configure(args: argparse.Namespace) -> int:
    store = _load_store(args)
    store.prepare()
    updated: list[str] = []

    job_preferences = resolve_text_argument(args.job_preferences_text, args.job_preferences_file)
    if job_preferences is not None:
        store.write_job_preferences(job_preferences)
        updated.append("job_preferences")

    user_profile = resolve_text_argument(args.user_profile_text, args.user_profile_file)
    if user_profile is not None:
        store.write_user_profile(user_profile)
        updated.append("user_profile")

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
    custom_parameters.update(parse_generic_assignments(args.custom_param))
    if args.custom_param:
        store.write_custom_parameters(custom_parameters)
        updated.append("custom_parameters")

    for source_path in args.import_file:
        store.ingest_managed_file(source_path)
        updated.append(f"import_file:{Path(source_path).name}")

    for assignment in args.inline_file:
        filename, content = split_assignment(assignment)
        store.write_managed_text_file(name=filename, content=content, source_path="inline")
        updated.append(f"inline_file:{filename}")

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
    store = _load_store(args)
    store.prepare()
    seed_cli_environment(Path(args.memory_root).expanduser())

    # Auto-use a saved browser session if it exists in the agent's memory path.
    browser_data_dir = store.memory_path / "browser-data"
    if browser_data_dir.exists() and "HARNESSIQ_BROWSER_SESSION_DIR" not in os.environ:
        os.environ["HARNESSIQ_BROWSER_SESSION_DIR"] = str(browser_data_dir.resolve())

    model = _load_factory(args.model_factory)()
    if not hasattr(model, "generate_turn"):
        raise TypeError("Model factory must return an object that implements generate_turn(request).")
    browser_tools: Iterable[Any] = ()
    if args.browser_tools_factory:
        created_tools = _load_factory(args.browser_tools_factory)()
        if created_tools is None:
            browser_tools = ()
        elif isinstance(created_tools, (str, bytes)):
            raise TypeError("Browser tools factory must return an iterable of tool objects, not a string.")
        else:
            browser_tools = tuple(created_tools)
    runtime_overrides = _parse_runtime_assignments(args.runtime_param)
    runtime_config = _build_runtime_config(args.sink)
    agent = LinkedInJobApplierAgent.from_memory(
        model=model,
        memory_path=store.memory_path,
        browser_tools=tuple(browser_tools),
        runtime_overrides=runtime_overrides,
        runtime_config=runtime_config,
    )
    result = agent.run(max_cycles=args.max_cycles)

    # Print applied jobs summary to stdout so the user can see what the agent did.
    applied_jobs = store.read_applied_jobs()
    _print_applied_jobs_summary(applied_jobs, store.applied_jobs_path)

    emit_json(
        {
            "agent": args.agent,
            "instance_id": _optional_string(getattr(agent, "instance_id", None)),
            "instance_name": _optional_string(getattr(agent, "instance_name", None)),
            "ledger_run_id": agent.last_run_id,
            "memory_path": str(store.memory_path.resolve()),
            "applied_jobs_file": str(store.applied_jobs_path.resolve()),
            "result": {
                "cycles_completed": result.cycles_completed,
                "pause_reason": result.pause_reason,
                "resets": result.resets,
                "status": result.status,
            },
        }
    )
    return 0


def _handle_init_browser(args: argparse.Namespace) -> int:
    """Open a persistent browser session and wait for the user to log in to LinkedIn."""
    store = _load_store(args)
    store.prepare()
    browser_data_dir = store.memory_path / "browser-data"

    try:
        from harnessiq.integrations.linkedin_playwright import PlaywrightLinkedInSession
    except ImportError as exc:
        raise RuntimeError(
            "playwright is required. Install with: pip install playwright && python -m playwright install chromium"
        ) from exc

    session = PlaywrightLinkedInSession(session_dir=browser_data_dir)
    session.start()

    print(f"Browser session saved to: {browser_data_dir.resolve()}")
    print()
    print("Session saved. You can now run the agent with:")
    print(f"  harnessiq linkedin run \\")
    print(f"    --agent {args.agent} \\")
    print(f"    --model-factory harnessiq.integrations.grok_model:create_grok_model \\")
    print(f"    --browser-tools-factory harnessiq.integrations.linkedin_playwright:create_browser_tools \\")
    print(f"    --max-cycles 20")
    print()
    print("The browser session in the above directory will be reused automatically.")
    print("Press Enter to close the browser and exit.")
    input()
    session.stop()
    emit_json(
        {
            "agent": args.agent,
            "browser_data_dir": str(browser_data_dir.resolve()),
            "status": "session_saved",
        }
    )
    return 0


def _load_store(args: argparse.Namespace) -> LinkedInMemoryStore:
    return LinkedInMemoryStore(memory_path=resolve_memory_path(args.agent, args.memory_root))


def _parse_runtime_assignments(assignments: Sequence[str]) -> dict[str, Any]:
    return parse_manifest_parameter_assignments(
        assignments,
        manifest=LINKEDIN_HARNESS_MANIFEST,
        scope="runtime",
    )


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _build_summary(store: LinkedInMemoryStore) -> dict[str, Any]:
    return {
        "additional_prompt": store.read_additional_prompt(),
        "agent_identity": store.read_agent_identity(),
        "custom_parameters": store.read_custom_parameters(),
        "job_preferences": store.read_job_preferences(),
        "managed_files": [record.as_dict() for record in store.read_managed_files()],
        "memory_path": str(store.memory_path.resolve()),
        "runtime_parameters": store.read_runtime_parameters(),
        "user_profile": store.read_user_profile(),
    }


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


def _print_applied_jobs_summary(jobs: list[JobApplicationRecord], applied_jobs_path: Path) -> None:
    """Print a human-readable summary of job applications to stderr."""
    stream = sys.stderr
    print(file=stream)
    print("=" * 64, file=stream)
    if not jobs:
        print("  NO DURABLE LINKEDIN APPLICATION RECORDS FOUND", file=stream)
    else:
        print(f"  DURABLE LINKEDIN APPLICATION RECORDS ({len(jobs)} total)", file=stream)
        print("  " + "-" * 60, file=stream)
        for job in jobs:
            status_label = job.status.upper() if job.status else "?"
            print(f"  [{status_label}] {job.title} @ {job.company}", file=stream)
            print(f"           {job.url}", file=stream)
            if job.notes:
                print(f"           Note: {job.notes}", file=stream)
    print(file=stream)
    print("  Full records saved to:", file=stream)
    print(f"  {applied_jobs_path.resolve()}", file=stream)
    print("=" * 64, file=stream)
    print(file=stream)


def _print_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 0


__all__ = ["register_linkedin_commands"]
