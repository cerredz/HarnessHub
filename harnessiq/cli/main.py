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
    from harnessiq.cli.exa_outreach import register_exa_outreach_commands
    from harnessiq.cli.instagram import register_instagram_commands

    register_linkedin_commands(subparsers)
    register_leads_commands(subparsers)
    register_exa_outreach_commands(subparsers)
    register_instagram_commands(subparsers)
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
