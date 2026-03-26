"""CLI commands for bundled master prompt discovery and retrieval."""

from __future__ import annotations

import argparse

from harnessiq.cli.common import emit_json, resolve_repo_root
from harnessiq.master_prompts import get_prompt, get_prompt_text, list_prompt_keys, list_prompts
from harnessiq.master_prompts.session_injection import (
    activate_prompt_session,
    clear_prompt_session,
    get_active_prompt_session,
)


def register_master_prompt_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    prompts_parser = subparsers.add_parser("prompts", help="Inspect bundled master prompts")
    prompts_parser.set_defaults(command_handler=lambda args: _print_help(prompts_parser))
    prompts_subparsers = prompts_parser.add_subparsers(dest="prompts_command")

    list_parser = prompts_subparsers.add_parser("list", help="List bundled master prompts")
    list_parser.set_defaults(command_handler=_handle_list)

    show_parser = prompts_subparsers.add_parser("show", help="Render one bundled master prompt as JSON")
    show_parser.add_argument("key", help="Prompt key, derived from the prompt filename.")
    show_parser.set_defaults(command_handler=_handle_show)

    text_parser = prompts_subparsers.add_parser("text", help="Print the raw prompt text for one prompt")
    text_parser.add_argument("key", help="Prompt key, derived from the prompt filename.")
    text_parser.set_defaults(command_handler=_handle_text)

    activate_parser = prompts_subparsers.add_parser(
        "activate",
        help="Activate one bundled prompt as always-on project session context for Claude Code and Codex",
    )
    activate_parser.add_argument("key", help="Prompt key, derived from the prompt filename.")
    activate_parser.add_argument(
        "--repo-root",
        default=".",
        help="Project path used to resolve the repo root for generated instruction files.",
    )
    activate_parser.set_defaults(command_handler=_handle_activate)

    current_parser = prompts_subparsers.add_parser(
        "current",
        help="Show the currently active project-scoped master prompt, if any",
    )
    current_parser.add_argument(
        "--repo-root",
        default=".",
        help="Project path used to resolve the repo root for generated instruction files.",
    )
    current_parser.set_defaults(command_handler=_handle_current)

    clear_parser = prompts_subparsers.add_parser(
        "clear",
        help="Remove generated Claude Code and Codex prompt injection overlays",
    )
    clear_parser.add_argument(
        "--repo-root",
        default=".",
        help="Project path used to resolve the repo root for generated instruction files.",
    )
    clear_parser.set_defaults(command_handler=_handle_clear)


def _handle_list(args: argparse.Namespace) -> int:
    del args
    prompts = list_prompts()
    emit_json(
        {
            "count": len(prompts),
            "keys": list_prompt_keys(),
            "prompts": [
                {
                    "key": prompt.key,
                    "title": prompt.title,
                    "description": prompt.description,
                }
                for prompt in prompts
            ],
        }
    )
    return 0


def _handle_show(args: argparse.Namespace) -> int:
    prompt = get_prompt(args.key)
    emit_json(
        {
            "prompt": {
                "key": prompt.key,
                "title": prompt.title,
                "description": prompt.description,
                "prompt": prompt.prompt,
            }
        }
    )
    return 0


def _handle_text(args: argparse.Namespace) -> int:
    print(get_prompt_text(args.key))
    return 0


def _handle_activate(args: argparse.Namespace) -> int:
    activation = activate_prompt_session(args.key, repo_root=resolve_repo_root(args.repo_root))
    emit_json(activation.to_payload())
    return 0


def _handle_current(args: argparse.Namespace) -> int:
    repo_root = resolve_repo_root(args.repo_root)
    activation = get_active_prompt_session(repo_root=repo_root)
    if activation is None:
        emit_json(
            {
                "active": False,
                "prompt": None,
                "files": {
                    "claude": repo_root / ".claude" / "CLAUDE.md",
                    "codex": repo_root / "AGENTS.override.md",
                    "state": repo_root / ".harnessiq" / "master_prompt_session" / "active_prompt.json",
                },
            }
        )
        return 0
    emit_json(activation.to_payload())
    return 0


def _handle_clear(args: argparse.Namespace) -> int:
    emit_json(clear_prompt_session(repo_root=resolve_repo_root(args.repo_root)))
    return 0


def _print_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 0


__all__ = ["register_master_prompt_commands"]
