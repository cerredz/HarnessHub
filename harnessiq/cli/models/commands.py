"""CLI commands for persisted model profiles."""

from __future__ import annotations

import argparse

from harnessiq.cli.common import emit_json
from harnessiq.config import ModelProfile, ModelProfileStore
from harnessiq.integrations import parse_model_spec


def register_model_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("models", help="Manage reusable provider-backed model profiles")
    parser.set_defaults(command_handler=lambda args: _print_help(parser))
    models_subparsers = parser.add_subparsers(dest="models_command")

    add_parser = models_subparsers.add_parser("add", help="Add or update a persisted model profile")
    add_parser.add_argument("--name", required=True, help="Unique profile name, for example work.")
    add_parser.add_argument(
        "--model",
        required=True,
        help="Provider-backed model reference in the form provider:model_name, for example openai:gpt-5.4.",
    )
    add_parser.add_argument("--temperature", type=float, help="Optional temperature override for the profile.")
    add_parser.add_argument(
        "--max-output-tokens",
        type=int,
        help="Optional output-token cap applied by the provider-backed adapter.",
    )
    add_parser.add_argument(
        "--reasoning-effort",
        choices=("low", "medium", "high"),
        help="Optional reasoning-effort override used by providers that support it.",
    )
    add_parser.set_defaults(command_handler=_handle_add)

    list_parser = models_subparsers.add_parser("list", help="List persisted model profiles")
    list_parser.set_defaults(command_handler=_handle_list)


def _handle_add(args: argparse.Namespace) -> int:
    provider, model_name = parse_model_spec(args.model)
    profile = ModelProfile(
        name=args.name,
        provider=provider,
        model_name=model_name,
        temperature=args.temperature,
        max_output_tokens=args.max_output_tokens,
        reasoning_effort=args.reasoning_effort,
    )
    store = ModelProfileStore()
    config_path = store.upsert(profile)
    emit_json(
        {
            "config_path": str(config_path),
            "profile": profile.as_dict(),
            "status": "saved",
        }
    )
    return 0


def _handle_list(args: argparse.Namespace) -> int:
    del args
    store = ModelProfileStore()
    catalog = store.load()
    emit_json(
        {
            "config_path": str(store.config_path),
            "profiles": [profile.as_dict() for profile in catalog.profiles],
        }
    )
    return 0


def _print_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 0


__all__ = ["register_model_commands"]
