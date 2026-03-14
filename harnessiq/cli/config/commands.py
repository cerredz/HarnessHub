"""CLI commands for repo-local credential bindings."""

from __future__ import annotations

import argparse
import json
from typing import Any

from harnessiq.config import (
    AgentCredentialBinding,
    CredentialEnvReference,
    CredentialsConfigStore,
    binding_field_map,
)


def register_config_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("config", help="Manage repo-local credential bindings")
    parser.set_defaults(command_handler=lambda args: _print_help(parser))
    config_subparsers = parser.add_subparsers(dest="config_command")

    set_parser = config_subparsers.add_parser("set", help="Create or update an agent credential binding")
    set_parser.add_argument("--agent", required=True, help="Logical agent name for this credential binding.")
    set_parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root that contains the .env file and .harnessiq credentials config.",
    )
    set_parser.add_argument("--description", help="Optional free-form description for this binding.")
    set_parser.add_argument(
        "--credential",
        action="append",
        default=[],
        metavar="FIELD=ENV_VAR",
        help="Map one credential field to an environment variable. Repeat for multiple fields.",
    )
    set_parser.set_defaults(command_handler=_handle_set)

    show_parser = config_subparsers.add_parser("show", help="Show one or all stored credential bindings")
    show_parser.add_argument("--agent", help="Optional logical agent name to show.")
    show_parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root that contains the .env file and .harnessiq credentials config.",
    )
    show_parser.add_argument(
        "--resolve",
        action="store_true",
        help="Resolve the selected binding against the repo-local .env and render redacted values.",
    )
    show_parser.set_defaults(command_handler=_handle_show)


def _handle_set(args: argparse.Namespace) -> int:
    if not args.credential:
        raise ValueError("At least one --credential FIELD=ENV_VAR assignment is required.")
    binding = AgentCredentialBinding(
        agent_name=args.agent,
        references=tuple(_parse_credential_assignments(args.credential)),
        description=args.description,
    )
    store = CredentialsConfigStore(repo_root=args.repo_root)
    store.upsert(binding)
    _emit_json(
        {
            "agent": binding.agent_name,
            "binding": _binding_payload(binding),
            "config_path": str(store.config_path),
            "status": "configured",
        }
    )
    return 0


def _handle_show(args: argparse.Namespace) -> int:
    store = CredentialsConfigStore(repo_root=args.repo_root)
    config = store.load()
    if args.agent:
        binding = config.binding_for(args.agent)
        payload: dict[str, Any] = {
            "agent": binding.agent_name,
            "binding": _binding_payload(binding),
            "config_path": str(store.config_path),
        }
        if args.resolve:
            payload["resolved"] = store.resolve_agent(binding.agent_name).as_redacted_dict()
        _emit_json(payload)
        return 0

    payload = {
        "bindings": [_binding_payload(binding) for binding in config.bindings],
        "config_path": str(store.config_path),
    }
    _emit_json(payload)
    return 0


def _parse_credential_assignments(assignments: list[str]) -> list[CredentialEnvReference]:
    parsed: list[CredentialEnvReference] = []
    for assignment in assignments:
        field_name, env_var = _split_assignment(assignment)
        parsed.append(CredentialEnvReference(field_name=field_name, env_var=env_var))
    return parsed


def _split_assignment(assignment: str) -> tuple[str, str]:
    key, separator, value = assignment.partition("=")
    if not separator:
        raise ValueError(f"Expected FIELD=ENV_VAR assignment, received '{assignment}'.")
    normalized_key = key.strip()
    normalized_value = value.strip()
    if not normalized_key:
        raise ValueError(f"Expected a non-empty field name in assignment '{assignment}'.")
    if not normalized_value:
        raise ValueError(f"Expected a non-empty env var in assignment '{assignment}'.")
    return normalized_key, normalized_value


def _binding_payload(binding: AgentCredentialBinding) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "agent_name": binding.agent_name,
        "field_map": binding_field_map(binding),
    }
    if binding.description is not None:
        payload["description"] = binding.description
    return payload


def _emit_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _print_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 0


__all__ = ["register_config_commands"]
