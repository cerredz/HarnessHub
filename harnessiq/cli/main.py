"""Top-level argparse entrypoint for Harnessiq."""

from __future__ import annotations

import argparse
from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="harnessiq", description="Harnessiq command-line interface")
    subparsers = parser.add_subparsers(dest="command")
    parser.set_defaults(command_handler=lambda args: _print_help(parser))

    from harnessiq.cli.linkedin import register_linkedin_commands
    from harnessiq.cli.leads import register_leads_commands
    from harnessiq.cli.master_prompts import register_master_prompt_commands
    from harnessiq.cli.models import register_model_commands
    from harnessiq.cli.exa_outreach import register_exa_outreach_commands
    from harnessiq.cli.instagram import register_instagram_commands
    from harnessiq.cli.ledger import register_ledger_commands
    from harnessiq.cli.commands import register_platform_commands
    from harnessiq.cli.prospecting import register_prospecting_commands

    register_platform_commands(subparsers)
    register_ledger_commands(subparsers)
    register_master_prompt_commands(subparsers)
    register_model_commands(subparsers)
    register_linkedin_commands(subparsers)
    register_leads_commands(subparsers)
    register_exa_outreach_commands(subparsers)
    register_instagram_commands(subparsers)
    register_prospecting_commands(subparsers)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    handler = getattr(args, "command_handler", None)
    if handler is None:
        return _print_help(parser)
    return int(handler(args) or 0)


def _print_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 0


__all__ = ["build_parser", "main"]
