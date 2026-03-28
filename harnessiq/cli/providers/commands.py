"""CLI commands for provider catalog discovery."""

from __future__ import annotations

import argparse
from collections import defaultdict

from harnessiq.cli.common import emit_json
from harnessiq.config import get_provider_credential_spec
from harnessiq.toolset.catalog import PROVIDER_ENTRIES, PROVIDER_FACTORY_MAP


def register_providers_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("providers", help="Inspect provider-backed tool families")
    parser.set_defaults(command_handler=lambda args: _print_help(parser))
    providers_subparsers = parser.add_subparsers(dest="providers_command")

    list_parser = providers_subparsers.add_parser("list", help="List provider families in the catalog")
    list_parser.set_defaults(command_handler=_handle_list)

    show_parser = providers_subparsers.add_parser("show", help="Render one provider family as JSON")
    show_parser.add_argument("family", help="Provider family name.")
    show_parser.set_defaults(command_handler=_handle_show)


def _handle_list(args: argparse.Namespace) -> int:
    del args
    grouped: dict[str, list] = defaultdict(list)
    for entry in PROVIDER_ENTRIES:
        grouped[entry.family].append(entry)

    providers = [_provider_payload(family, entries) for family, entries in sorted(grouped.items())]
    emit_json({"count": len(providers), "providers": providers})
    return 0


def _handle_show(args: argparse.Namespace) -> int:
    family = args.family.strip().lower()
    if family not in PROVIDER_FACTORY_MAP:
        available = ", ".join(sorted(PROVIDER_FACTORY_MAP))
        raise KeyError(f"No provider family '{args.family}'. Available families: {available}.")
    entries = [entry for entry in PROVIDER_ENTRIES if entry.family == family]
    emit_json({"provider": _provider_payload(family, entries)})
    return 0


def _provider_payload(family: str, entries: list) -> dict[str, object]:
    requires_credentials = any(entry.requires_credentials for entry in entries)
    try:
        spec = get_provider_credential_spec(family)
        fields = [
            {"name": field.name, "description": field.description}
            for field in spec.fields
        ]
        description = spec.description
    except KeyError:
        spec = None
        fields = []
        description = entries[0].description
    return {
        "credential_fields": fields,
        "description": description,
        "example_env_assignments": _build_example_env_assignments(family, fields),
        "family": family,
        "factory": {
            "function": PROVIDER_FACTORY_MAP[family][1],
            "module": PROVIDER_FACTORY_MAP[family][0],
        },
        "requires_credentials": requires_credentials,
        "tool_keys": [entry.key for entry in entries],
    }


def _build_example_env_assignments(family: str, fields: list[dict[str, str]]) -> list[str]:
    return [
        f"{field['name']}={family.upper()}_{field['name'].upper()}"
        for field in fields
    ]


def _print_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 0


__all__ = ["register_providers_commands"]
