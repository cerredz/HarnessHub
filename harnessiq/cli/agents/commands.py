"""CLI commands for harness manifest discovery."""

from __future__ import annotations

import argparse

from harnessiq.cli.builders import HarnessCliLifecycleBuilder
from harnessiq.cli.common import emit_json
from harnessiq.shared.harness_manifests import get_harness_manifest, list_harness_manifests


def register_agents_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("agents", help="Inspect registered harness manifests")
    parser.set_defaults(command_handler=lambda args: _print_help(parser))
    agents_subparsers = parser.add_subparsers(dest="agents_command")

    list_parser = agents_subparsers.add_parser("list", help="List registered harness manifests")
    list_parser.set_defaults(command_handler=_handle_list)

    show_parser = agents_subparsers.add_parser("show", help="Render one harness manifest as JSON")
    show_parser.add_argument("manifest_id", help="Harness manifest id, CLI alias, or agent name.")
    show_parser.set_defaults(command_handler=_handle_show)


def _handle_list(args: argparse.Namespace) -> int:
    del args
    manifests = list_harness_manifests()
    emit_json(
        {
            "count": len(manifests),
            "agents": [
                {
                    "brief_description": f"{manifest.display_name} harness.",
                    "cli_command": manifest.cli_command,
                    "display_name": manifest.display_name,
                    "import_path": manifest.import_path,
                    "manifest_id": manifest.manifest_id,
                    "provider_families": list(manifest.provider_families),
                }
                for manifest in manifests
            ],
        }
    )
    return 0


def _handle_show(args: argparse.Namespace) -> int:
    manifest = get_harness_manifest(args.manifest_id)
    emit_json(HarnessCliLifecycleBuilder().build_inspection_payload(manifest=manifest))
    return 0


def _print_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 0


__all__ = ["register_agents_commands"]
