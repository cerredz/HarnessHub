"""CLI commands for global sink connections and local ledger querying."""

from __future__ import annotations

import argparse
from typing import Any

from harnessiq.cli.common import emit_json
from harnessiq.utils import (
    ConnectionsConfigStore,
    SinkConnection,
    build_ledger_report,
    build_sink_from_connection,
    export_ledger_entries,
    filter_ledger_entries,
    follow_ledger,
    load_ledger_entries,
    render_ledger_report,
)


def register_ledger_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    connect_parser = subparsers.add_parser("connect", help="Configure a global output sink connection")
    connect_parser.set_defaults(command_handler=lambda args: _print_help(connect_parser))
    connect_subparsers = connect_parser.add_subparsers(dest="connect_command")

    _register_connect_command(
        connect_subparsers,
        "obsidian",
        [("vault-path", True), ("note-folder", False), ("filename-template", False)],
    )
    _register_connect_command(connect_subparsers, "slack", [("webhook-url", True)])
    _register_connect_command(connect_subparsers, "discord", [("webhook-url", True)])
    _register_connect_command(connect_subparsers, "notion", [("api-token", True), ("database-id", True)])
    _register_connect_command(
        connect_subparsers,
        "confluence",
        [("base-url", True), ("api-token", True), ("space-key", True), ("parent-page-id", False)],
    )
    _register_connect_command(
        connect_subparsers,
        "supabase",
        [("base-url", True), ("api-key", True), ("table", False), ("schema", False)],
    )
    _register_connect_command(
        connect_subparsers,
        "linear",
        [("api-key", True), ("team-id", True), ("explode-field", False)],
    )

    connections_parser = subparsers.add_parser("connections", help="Inspect or manage configured sink connections")
    connections_parser.set_defaults(command_handler=lambda args: _print_help(connections_parser))
    connections_subparsers = connections_parser.add_subparsers(dest="connections_command")

    list_parser = connections_subparsers.add_parser("list", help="List configured sink connections")
    list_parser.set_defaults(command_handler=_handle_connections_list)

    remove_parser = connections_subparsers.add_parser("remove", help="Remove a configured sink connection")
    remove_parser.add_argument("name")
    remove_parser.set_defaults(command_handler=_handle_connections_remove)

    test_parser = connections_subparsers.add_parser("test", help="Validate that a sink connection can be constructed")
    test_parser.add_argument("name")
    test_parser.set_defaults(command_handler=_handle_connections_test)

    logs_parser = subparsers.add_parser("logs", help="Inspect the local audit ledger")
    logs_parser.add_argument("--agent", help="Filter to a single agent name.")
    logs_parser.add_argument("--since", help="Relative time filter such as 30m, 6h, or 7d.")
    logs_parser.add_argument("--format", default="json", choices=("json", "jsonl", "markdown"))
    logs_parser.add_argument("--ledger-path", help="Override the default ledger path.")
    logs_parser.add_argument("--follow", action="store_true", default=False)
    logs_parser.set_defaults(command_handler=_handle_logs)

    export_parser = subparsers.add_parser("export", help="Export ledger entries in a structured format")
    export_parser.add_argument("--agent", help="Filter to a single agent name.")
    export_parser.add_argument("--since", help="Relative time filter such as 30m, 6h, or 7d.")
    export_parser.add_argument("--format", default="json", choices=("json", "jsonl", "csv", "markdown"))
    export_parser.add_argument("--ledger-path", help="Override the default ledger path.")
    export_parser.add_argument("--flatten-outputs", action="store_true", default=False)
    export_parser.set_defaults(command_handler=_handle_export)

    report_parser = subparsers.add_parser("report", help="Build a cross-agent report from the local ledger")
    report_parser.add_argument("--agent", help="Filter to a single agent name.")
    report_parser.add_argument("--since", help="Relative time filter such as 30m, 6h, or 7d.")
    report_parser.add_argument("--format", default="markdown", choices=("markdown", "json"))
    report_parser.add_argument("--ledger-path", help="Override the default ledger path.")
    report_parser.set_defaults(command_handler=_handle_report)


def _register_connect_command(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    sink_type: str,
    options: list[tuple[str, bool]],
) -> None:
    parser = subparsers.add_parser(sink_type, help=f"Configure a global {sink_type} sink")
    parser.add_argument("--name", default=sink_type)
    for option_name, required in options:
        parser.add_argument(f"--{option_name}", required=required)
    parser.set_defaults(command_handler=_handle_connect, sink_type=sink_type)


def _handle_connect(args: argparse.Namespace) -> int:
    config = {
        key.replace("_", "-").replace("-", "_"): value
        for key, value in vars(args).items()
        if key not in {"command", "command_handler", "connect_command", "name", "sink_type"} and value is not None
    }
    connection = SinkConnection(
        name=str(args.name),
        sink_type=str(args.sink_type),
        config=config,
        enabled=True,
    )
    store = ConnectionsConfigStore()
    path = store.upsert(connection)
    emit_json({"config_path": str(path), "connection": connection.as_dict(), "status": "connected"})
    return 0


def _handle_connections_list(args: argparse.Namespace) -> int:
    del args
    store = ConnectionsConfigStore()
    payload = [connection.as_dict() for connection in store.load().connections]
    emit_json({"connections": payload})
    return 0


def _handle_connections_remove(args: argparse.Namespace) -> int:
    store = ConnectionsConfigStore()
    path = store.remove(args.name)
    emit_json({"config_path": str(path), "removed": args.name, "status": "removed"})
    return 0


def _handle_connections_test(args: argparse.Namespace) -> int:
    store = ConnectionsConfigStore()
    config = store.load()
    indexed = {connection.name: connection for connection in config.connections}
    if args.name not in indexed:
        raise ValueError(f"No sink connection named '{args.name}' exists.")
    connection = indexed[args.name]
    sink = build_sink_from_connection(connection)
    emit_json(
        {
            "connection": connection.as_dict(),
            "sink_class": type(sink).__name__,
            "status": "validated",
        }
    )
    return 0


def _handle_logs(args: argparse.Namespace) -> int:
    if args.follow:
        follow_ledger(args.ledger_path)
        return 0
    entries = _load_filtered_entries(agent=args.agent, since=args.since, ledger_path=args.ledger_path)
    rendered = export_ledger_entries(entries, output_format=args.format)
    print(rendered)
    return 0


def _handle_export(args: argparse.Namespace) -> int:
    entries = _load_filtered_entries(agent=args.agent, since=args.since, ledger_path=args.ledger_path)
    rendered = export_ledger_entries(
        entries,
        output_format=args.format,
        flatten_outputs=bool(args.flatten_outputs),
    )
    print(rendered)
    return 0


def _handle_report(args: argparse.Namespace) -> int:
    entries = _load_filtered_entries(agent=args.agent, since=args.since, ledger_path=args.ledger_path)
    report = build_ledger_report(entries)
    rendered = render_ledger_report(report, output_format=args.format)
    print(rendered)
    return 0


def _load_filtered_entries(*, agent: str | None, since: str | None, ledger_path: str | None):
    entries = load_ledger_entries(ledger_path)
    return filter_ledger_entries(entries, agent_name=agent, since=since)


def _print_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 0


__all__ = ["register_ledger_commands"]
