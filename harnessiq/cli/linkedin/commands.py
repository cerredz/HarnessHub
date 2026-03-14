"""LinkedIn CLI commands for managed memory and agent execution."""

from __future__ import annotations

import argparse
import importlib
import json
import re
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from harnessiq.agents import LinkedInJobApplierAgent, LinkedInMemoryStore
from harnessiq.agents.linkedin import SUPPORTED_LINKEDIN_RUNTIME_PARAMETERS, normalize_linkedin_runtime_parameters


def register_linkedin_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("linkedin", help="Manage and run the LinkedIn agent")
    parser.set_defaults(command_handler=lambda args: _print_help(parser))
    linkedin_subparsers = parser.add_subparsers(dest="linkedin_command")

    prepare_parser = linkedin_subparsers.add_parser("prepare", help="Create or refresh a LinkedIn agent memory folder")
    _add_agent_options(prepare_parser)
    prepare_parser.set_defaults(command_handler=_handle_prepare)

    configure_parser = linkedin_subparsers.add_parser(
        "configure",
        help="Write LinkedIn memory inputs, custom parameters, and managed files",
    )
    _add_agent_options(configure_parser)
    _add_text_or_file_options(configure_parser, "job_preferences", "Job preferences")
    _add_text_or_file_options(configure_parser, "user_profile", "User profile")
    _add_text_or_file_options(configure_parser, "agent_identity", "Agent identity")
    _add_text_or_file_options(configure_parser, "additional_prompt", "Additional prompt")
    configure_parser.add_argument(
        "--runtime-param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help=f"Persist a LinkedIn runtime parameter. Supported keys: {', '.join(SUPPORTED_LINKEDIN_RUNTIME_PARAMETERS)}.",
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
    _add_agent_options(show_parser)
    show_parser.set_defaults(command_handler=_handle_show)

    run_parser = linkedin_subparsers.add_parser("run", help="Run the LinkedIn SDK agent from persisted CLI state")
    _add_agent_options(run_parser)
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
    run_parser.add_argument("--max-cycles", type=int, help="Optional max cycle count passed to agent.run().")
    run_parser.set_defaults(command_handler=_handle_run)


def _add_agent_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--agent", required=True, help="Logical LinkedIn agent name used to resolve the memory folder.")
    parser.add_argument(
        "--memory-root",
        default="memory/linkedin",
        help="Root directory that holds per-agent LinkedIn memory folders.",
    )


def _add_text_or_file_options(parser: argparse.ArgumentParser, field_name: str, label: str) -> None:
    group = parser.add_mutually_exclusive_group()
    option_name = field_name.replace("_", "-")
    group.add_argument(f"--{option_name}-text", help=f"{label} content provided inline.")
    group.add_argument(f"--{option_name}-file", help=f"Path to a UTF-8 text file containing {label.lower()} content.")


def _handle_prepare(args: argparse.Namespace) -> int:
    store = _load_store(args)
    store.prepare()
    _emit_json({"agent": args.agent, "memory_path": str(store.memory_path.resolve()), "status": "prepared"})
    return 0


def _handle_configure(args: argparse.Namespace) -> int:
    store = _load_store(args)
    store.prepare()
    updated: list[str] = []

    job_preferences = _resolve_text_argument(args.job_preferences_text, args.job_preferences_file)
    if job_preferences is not None:
        store.write_job_preferences(job_preferences)
        updated.append("job_preferences")

    user_profile = _resolve_text_argument(args.user_profile_text, args.user_profile_file)
    if user_profile is not None:
        store.write_user_profile(user_profile)
        updated.append("user_profile")

    agent_identity = _resolve_text_argument(args.agent_identity_text, args.agent_identity_file)
    if agent_identity is not None:
        store.write_agent_identity(agent_identity)
        updated.append("agent_identity")

    additional_prompt = _resolve_text_argument(args.additional_prompt_text, args.additional_prompt_file)
    if additional_prompt is not None:
        store.write_additional_prompt(additional_prompt)
        updated.append("additional_prompt")

    runtime_parameters = store.read_runtime_parameters()
    runtime_parameters.update(_parse_runtime_assignments(args.runtime_param))
    if args.runtime_param:
        store.write_runtime_parameters(runtime_parameters)
        updated.append("runtime_parameters")

    custom_parameters = store.read_custom_parameters()
    custom_parameters.update(_parse_generic_assignments(args.custom_param))
    if args.custom_param:
        store.write_custom_parameters(custom_parameters)
        updated.append("custom_parameters")

    for source_path in args.import_file:
        store.ingest_managed_file(source_path)
        updated.append(f"import_file:{Path(source_path).name}")

    for assignment in args.inline_file:
        filename, content = _split_assignment(assignment)
        store.write_managed_text_file(name=filename, content=content, source_path="inline")
        updated.append(f"inline_file:{filename}")

    payload = _build_summary(store)
    payload["updated"] = updated
    payload["status"] = "configured"
    _emit_json(payload)
    return 0


def _handle_show(args: argparse.Namespace) -> int:
    store = _load_store(args)
    store.prepare()
    _emit_json(_build_summary(store))
    return 0


def _handle_run(args: argparse.Namespace) -> int:
    store = _load_store(args)
    store.prepare()
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
    agent = LinkedInJobApplierAgent.from_memory(
        model=model,
        memory_path=store.memory_path,
        browser_tools=tuple(browser_tools),
        runtime_overrides=runtime_overrides,
    )
    result = agent.run(max_cycles=args.max_cycles)
    _emit_json(
        {
            "agent": args.agent,
            "memory_path": str(store.memory_path.resolve()),
            "result": {
                "cycles_completed": result.cycles_completed,
                "pause_reason": result.pause_reason,
                "resets": result.resets,
                "status": result.status,
            },
        }
    )
    return 0


def _load_store(args: argparse.Namespace) -> LinkedInMemoryStore:
    return LinkedInMemoryStore(memory_path=_resolve_memory_path(args.agent, args.memory_root))


def _resolve_memory_path(agent_name: str, memory_root: str) -> Path:
    return Path(memory_root).expanduser() / _slugify_agent_name(agent_name)


def _slugify_agent_name(agent_name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", agent_name.strip()).strip("-")
    if not cleaned:
        raise ValueError("Agent names must contain at least one alphanumeric character.")
    return cleaned


def _resolve_text_argument(text_value: str | None, file_value: str | None) -> str | None:
    if text_value is not None:
        return text_value
    if file_value is not None:
        return Path(file_value).read_text(encoding="utf-8")
    return None


def _parse_runtime_assignments(assignments: Sequence[str]) -> dict[str, Any]:
    return normalize_linkedin_runtime_parameters(_parse_generic_assignments(assignments))


def _parse_generic_assignments(assignments: Sequence[str]) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for assignment in assignments:
        key, raw_value = _split_assignment(assignment)
        parsed[key] = _parse_scalar(raw_value)
    return parsed


def _split_assignment(assignment: str) -> tuple[str, str]:
    key, separator, value = assignment.partition("=")
    if not separator:
        raise ValueError(f"Expected KEY=VALUE assignment, received '{assignment}'.")
    normalized_key = key.strip()
    if not normalized_key:
        raise ValueError(f"Expected a non-empty key in assignment '{assignment}'.")
    return normalized_key, value


def _parse_scalar(value: str) -> Any:
    trimmed = value.strip()
    if not trimmed:
        return ""
    try:
        return json.loads(trimmed)
    except json.JSONDecodeError:
        return value


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


def _emit_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _print_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 0


__all__ = ["register_linkedin_commands"]
