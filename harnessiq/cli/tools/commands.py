"""CLI commands for tool catalog discovery and validation."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from harnessiq.cli.common import emit_json
from harnessiq.config import get_provider_credential_spec
from harnessiq.shared.tools import RegisteredTool
from harnessiq.toolset import ToolsetRegistry, define_tool, list_tools
from harnessiq.toolset.catalog import PROVIDER_ENTRIES, PROVIDER_FACTORY_MAP


def register_tools_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("tools", help="Inspect the registered HarnessIQ tool catalog")
    parser.set_defaults(command_handler=lambda args: _print_help(parser))
    tools_subparsers = parser.add_subparsers(dest="tools_command")

    list_parser = tools_subparsers.add_parser("list", help="List tool entries in the catalog")
    list_parser.add_argument("--family", help="Filter to one tool family.")
    credential_group = list_parser.add_mutually_exclusive_group()
    credential_group.add_argument(
        "--provider",
        action="store_true",
        help="Show only provider-backed tools that require credentials.",
    )
    credential_group.add_argument(
        "--builtin",
        action="store_true",
        help="Show only built-in tools that do not require credentials.",
    )
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="JSON is already the default output format; this flag is accepted for compatibility.",
    )
    list_parser.set_defaults(command_handler=_handle_list)

    show_parser = tools_subparsers.add_parser("show", help="Render one tool definition as JSON")
    show_parser.add_argument("key", help="Tool key in namespace.name format.")
    show_parser.set_defaults(command_handler=_handle_show)

    families_parser = tools_subparsers.add_parser("families", help="List tool families and counts")
    families_parser.set_defaults(command_handler=_handle_families)

    validate_parser = tools_subparsers.add_parser(
        "validate",
        help="Validate a JSON custom-tool specification from a file path or stdin ('-')",
    )
    validate_parser.add_argument("source", help="Path to a JSON file or '-' to read from stdin.")
    validate_parser.set_defaults(command_handler=_handle_validate)

    import_parser = tools_subparsers.add_parser(
        "import",
        help="Validate a JSON custom-tool specification intended for Python-backed tool registration",
    )
    import_parser.add_argument("source", help="Path to a JSON file or '-' to read from stdin.")
    import_parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate the spec without attempting any runtime registration.",
    )
    import_parser.set_defaults(command_handler=_handle_import)


def _handle_list(args: argparse.Namespace) -> int:
    del args.json
    entries = list_tools()
    if args.family:
        entries = [entry for entry in entries if entry.family == args.family.strip()]
    if args.provider:
        entries = [entry for entry in entries if entry.requires_credentials]
    if args.builtin:
        entries = [entry for entry in entries if not entry.requires_credentials]
    emit_json(
        {
            "count": len(entries),
            "filters": {
                "builtin_only": bool(args.builtin),
                "family": args.family,
                "provider_only": bool(args.provider),
            },
            "tools": [_tool_entry_payload(entry) for entry in entries],
        }
    )
    return 0


def _handle_show(args: argparse.Namespace) -> int:
    tool = _resolve_tool_for_inspection(args.key)
    emit_json({"tool": tool.inspect()})
    return 0


def _handle_families(args: argparse.Namespace) -> int:
    del args
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in list_tools():
        grouped[entry.family].append(_tool_entry_payload(entry))

    payload = []
    for family in sorted(grouped):
        entries = grouped[family]
        requires_credentials_values = {bool(item["requires_credentials"]) for item in entries}
        if requires_credentials_values == {True}:
            credential_mode = "requires_credentials"
        elif requires_credentials_values == {False}:
            credential_mode = "builtin"
        else:
            credential_mode = "mixed"
        payload.append(
            {
                "family": family,
                "credential_mode": credential_mode,
                "count": len(entries),
                "requires_credentials": credential_mode == "requires_credentials",
                "tool_keys": [item["key"] for item in entries],
            }
        )

    emit_json({"count": len(payload), "families": payload})
    return 0


def _handle_validate(args: argparse.Namespace) -> int:
    return _emit_validation_result(args.source)


def _handle_import(args: argparse.Namespace) -> int:
    payload = _load_tool_spec_payload(args.source)
    validated, error = _validate_tool_spec_payload(payload)
    emit_json(
        {
            "source": args.source,
            "validate_only": bool(args.validate_only),
            "valid": validated is not None,
            "tool": (validated.definition.inspect() if validated is not None else None),
            "registered": False,
            "status": "validated" if validated is not None else "invalid",
            "note": (
                "Runtime registration is not supported from JSON because handlers are Python-only."
                if validated is not None
                else None
            ),
            "error": error,
        }
    )
    return 0 if validated is not None else 1


def _emit_validation_result(source: str) -> int:
    payload = _load_tool_spec_payload(source)
    validated, error = _validate_tool_spec_payload(payload)
    emit_json(
        {
            "source": source,
            "valid": validated is not None,
            "tool": (validated.definition.inspect() if validated is not None else None),
            "status": "validated" if validated is not None else "invalid",
            "error": error,
        }
    )
    return 0 if validated is not None else 1


def _tool_entry_payload(entry) -> dict[str, Any]:
    return {
        "description": entry.description,
        "family": entry.family,
        "key": entry.key,
        "name": entry.name,
        "requires_credentials": entry.requires_credentials,
    }


def _load_tool_spec_payload(source: str) -> dict[str, Any]:
    if source == "-":
        raw = sys.stdin.read()
    else:
        raw = Path(source).read_text(encoding="utf-8")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("Tool spec input must be a JSON object.")
    return payload


def _validate_tool_spec_payload(payload: dict[str, Any]) -> tuple[RegisteredTool | None, str | None]:
    try:
        parameters = payload.get("parameters", {})
        required = payload.get("required", ())
        if not isinstance(parameters, dict):
            raise ValueError("Tool spec 'parameters' must be a JSON object.")
        if not isinstance(required, (list, tuple)):
            raise ValueError("Tool spec 'required' must be a JSON array when provided.")
        tool = define_tool(
            key=str(payload["key"]),
            name=(str(payload["name"]) if payload.get("name") is not None else None),
            description=str(payload["description"]),
            parameters=parameters,
            required=[str(value) for value in required],
            additional_properties=bool(payload.get("additional_properties", False)),
            tool_type=str(payload.get("tool_type", "function")),
            handler=lambda arguments: arguments,
        )
    except Exception as exc:  # pragma: no cover - exercised by CLI tests
        return None, str(exc)
    return tool, None


def _resolve_tool_for_inspection(key: str) -> RegisteredTool:
    if key in {entry.key for entry in PROVIDER_ENTRIES}:
        family = key.split(".", 1)[0]
        return _resolve_provider_tool_for_inspection(family, key)
    return ToolsetRegistry().get(key)


def _resolve_provider_tool_for_inspection(family: str, key: str) -> RegisteredTool:
    module_path, factory_name = PROVIDER_FACTORY_MAP[family]
    module = importlib.import_module(module_path)
    factory = getattr(module, factory_name)
    credentials = _placeholder_credentials_for_family(family)
    tools = tuple(factory(credentials=credentials))
    for tool in tools:
        if tool.key == key:
            return tool
    raise KeyError(f"Provider family '{family}' did not expose tool '{key}'.")


def _placeholder_credentials_for_family(family: str) -> object | None:
    matching_entries = [entry for entry in PROVIDER_ENTRIES if entry.family == family]
    if matching_entries and not any(entry.requires_credentials for entry in matching_entries):
        return None
    spec = get_provider_credential_spec(family)
    return spec.build_credentials({field_name: f"{family}_{field_name}_placeholder" for field_name in spec.field_names})


def _print_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 0


__all__ = ["register_tools_commands"]
