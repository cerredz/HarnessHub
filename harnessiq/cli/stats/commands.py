"""CLI commands for ledger-derived stats and analytics snapshots."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Mapping

from harnessiq.cli.common import emit_json
from harnessiq.utils import (
    StatsProjector,
    StatsRebuildResult,
    build_stats_summary,
    export_stats_csv,
    export_stats_json,
    load_stats_snapshots,
)


def register_stats_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    stats_parser = subparsers.add_parser("stats", help="Inspect local stats and analytics snapshots")
    stats_parser.set_defaults(command_handler=lambda args: _print_help(stats_parser))
    stats_subparsers = stats_parser.add_subparsers(dest="stats_command")

    summary_parser = stats_subparsers.add_parser("summary", help="Print repo-wide stats summary")
    summary_parser.add_argument("--format", default="table", choices=("table", "json"))
    summary_parser.add_argument("--ledger-path", help="Override the default ledger path.")
    summary_parser.set_defaults(command_handler=_handle_summary)

    agent_parser = stats_subparsers.add_parser("agent", help="Print one agent aggregate snapshot")
    agent_parser.add_argument("agent_name")
    agent_parser.add_argument("--format", default="table", choices=("table", "json"))
    agent_parser.add_argument("--ledger-path", help="Override the default ledger path.")
    agent_parser.set_defaults(command_handler=_handle_agent)

    session_parser = stats_subparsers.add_parser("session", help="Print one session snapshot")
    session_parser.add_argument("session_id")
    session_parser.add_argument("--format", default="table", choices=("table", "json"))
    session_parser.add_argument("--ledger-path", help="Override the default ledger path.")
    session_parser.set_defaults(command_handler=_handle_session)

    instance_parser = stats_subparsers.add_parser("instance", help="Print one instance aggregate snapshot")
    instance_parser.add_argument("instance_id")
    instance_parser.add_argument("--format", default="table", choices=("table", "json"))
    instance_parser.add_argument("--ledger-path", help="Override the default ledger path.")
    instance_parser.set_defaults(command_handler=_handle_instance)

    rebuild_parser = stats_subparsers.add_parser("rebuild", help="Rebuild all stats snapshots from the ledger")
    rebuild_parser.add_argument("--format", default="table", choices=("table", "json"))
    rebuild_parser.add_argument("--ledger-path", help="Override the default ledger path.")
    rebuild_parser.set_defaults(command_handler=_handle_rebuild)

    export_parser = stats_subparsers.add_parser("export", help="Export stats snapshots or flat per-run CSV")
    export_parser.add_argument("--format", required=True, choices=("json", "csv"))
    export_parser.add_argument("--output", help="Write the export to a file instead of stdout.")
    export_parser.add_argument("--ledger-path", help="Override the default ledger path.")
    export_parser.set_defaults(command_handler=_handle_export)


def _handle_summary(args: argparse.Namespace) -> int:
    summary = build_stats_summary(args.ledger_path)
    if args.format == "json":
        emit_json(summary)
    else:
        print(_render_summary(summary))
    return 0


def _handle_agent(args: argparse.Namespace) -> int:
    record = _lookup_snapshot_record("agents", args.agent_name, ledger_path=args.ledger_path)
    if args.format == "json":
        emit_json(record)
    else:
        print(_render_agent_record(record))
    return 0


def _handle_session(args: argparse.Namespace) -> int:
    record = _lookup_snapshot_record("sessions", args.session_id, ledger_path=args.ledger_path)
    if args.format == "json":
        emit_json(record)
    else:
        print(_render_session_record(record))
    return 0


def _handle_instance(args: argparse.Namespace) -> int:
    record = _lookup_snapshot_record("instances", args.instance_id, ledger_path=args.ledger_path)
    if args.format == "json":
        emit_json(record)
    else:
        print(_render_instance_record(record))
    return 0


def _handle_rebuild(args: argparse.Namespace) -> int:
    result = StatsProjector(args.ledger_path).rebuild()
    if args.format == "json":
        emit_json(result.as_dict())
    else:
        print(_render_rebuild_result(result))
    return 0


def _handle_export(args: argparse.Namespace) -> int:
    if args.format == "json":
        rendered = export_stats_json(args.ledger_path)
    else:
        rendered = export_stats_csv(args.ledger_path)
    if args.output:
        output_path = Path(args.output).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
        print(f"Wrote {args.format} stats export to {output_path}")
    else:
        print(rendered)
    return 0


def _lookup_snapshot_record(
    snapshot_name: str,
    key: str,
    *,
    ledger_path: str | None,
) -> dict[str, Any]:
    snapshots = load_stats_snapshots(ledger_path)
    snapshot = snapshots[snapshot_name]
    if key not in snapshot:
        raise ValueError(f"No stats record named '{key}' exists in {snapshot_name}.")
    record = snapshot[key]
    if not isinstance(record, dict):
        raise ValueError(f"Stats record '{key}' in {snapshot_name} is malformed.")
    return record


def _render_summary(summary: Mapping[str, Any]) -> str:
    lines = [
        "harnessiq stats summary",
        "",
        "HarnessIQ Stats Summary",
        _row("Total runs", _format_int(summary.get("total_runs", 0))),
        _row("Total sessions", _format_int(summary.get("total_sessions", 0))),
        _row(
            "Completed",
            f"{_format_int(summary.get('completed_runs', 0))} ({_format_percent(summary.get('success_rate', 0.0))})",
        ),
        _row("Paused", _format_int(summary.get("paused_runs", 0))),
        _row("Error", _format_int(summary.get("error_runs", 0))),
        _row("Max cycles reached", _format_int(summary.get("max_cycles_reached_runs", 0))),
        _row("Tokens (estimated)", _format_int(summary.get("tokens_estimated", 0))),
        _row("Tokens (actual)", _format_optional_int(summary.get("tokens_actual"))),
        _row("Avg duration / run", _format_duration(summary.get("avg_duration_per_run", 0.0))),
        _row("Avg resets / run", _format_decimal(summary.get("avg_resets_per_run", 0.0))),
        _row("Avg cycles / run", _format_decimal(summary.get("avg_cycles_per_run", 0.0))),
        _row("Agents active", _format_joined(summary.get("agents_active"))),
        _row("Snapshot last updated", str(summary.get("snapshot_last_updated") or "—")),
    ]
    return "\n".join(lines)


def _render_agent_record(record: Mapping[str, Any]) -> str:
    lines = [
        f"harnessiq stats agent {record.get('agent_name', '')}".rstrip(),
        "",
        "Agent Stats",
        _row("Agent name", str(record.get("agent_name") or "")),
        _row("Last updated", str(record.get("last_updated") or "—")),
        _row("Total runs", _format_int(record.get("total_runs", 0))),
        _row("Completed runs", _format_int(record.get("completed_runs", 0))),
        _row("Paused runs", _format_int(record.get("paused_runs", 0))),
        _row("Error runs", _format_int(record.get("error_runs", 0))),
        _row("Max cycles reached", _format_int(record.get("max_cycles_reached_runs", 0))),
        _row("Success rate", _format_percent(record.get("success_rate", 0.0))),
        _row("Total sessions", _format_int(record.get("total_sessions", 0))),
        _row("Lifetime tokens (estimated)", _format_int(record.get("lifetime_tokens_estimated", 0))),
        _row("Lifetime tokens (actual)", _format_optional_int(record.get("lifetime_tokens_actual"))),
        _row("Avg resets / run", _format_decimal(record.get("avg_resets_per_run", 0.0))),
        _row("Avg cycles / run", _format_decimal(record.get("avg_cycles_per_run", 0.0))),
        _row("Avg duration / run", _format_duration(record.get("avg_duration_per_run", 0.0))),
        "Top tools",
    ]
    top_tools = record.get("top_tools")
    if isinstance(top_tools, list) and top_tools:
        for tool in top_tools:
            if not isinstance(tool, Mapping):
                continue
            lines.append(
                f"- {tool.get('tool_key', '')}: {_format_int(tool.get('total_calls', 0))}"
            )
    else:
        lines.append("- none")
    return "\n".join(lines)


def _render_session_record(record: Mapping[str, Any]) -> str:
    lines = [
        f"harnessiq stats session {record.get('session_id', '')}".rstrip(),
        "",
        "Session Stats",
        _row("Session id", str(record.get("session_id") or "")),
        _row("Instance id", str(record.get("instance_id") or "")),
        _row("Agent name", str(record.get("agent_name") or "")),
        _row("Run count", _format_int(record.get("run_count", 0))),
        _row("Session status", str(record.get("session_status") or "")),
        _row("Session started at", str(record.get("session_started_at") or "—")),
        _row("Session finished at", str(record.get("session_finished_at") or "—")),
        _row("Session duration", _format_duration(record.get("session_duration_seconds", 0.0))),
        _row("Session tokens (estimated)", _format_int(record.get("session_tokens_estimated", 0))),
        _row("Session tokens (actual)", _format_optional_int(record.get("session_tokens_actual"))),
        _row("Pause count", _format_int(record.get("pause_count", 0))),
        _row("Total resets", _format_int(record.get("total_resets", 0))),
        _row("Total cycles", _format_int(record.get("total_cycles", 0))),
        _row("Last updated", str(record.get("last_updated") or "—")),
        "Run ids",
    ]
    run_ids = record.get("run_ids")
    if isinstance(run_ids, list) and run_ids:
        for run_id in run_ids:
            lines.append(f"- {run_id}")
    else:
        lines.append("- none")
    return "\n".join(lines)


def _render_instance_record(record: Mapping[str, Any]) -> str:
    lines = [
        f"harnessiq stats instance {record.get('instance_id', '')}".rstrip(),
        "",
        "Instance Stats",
        _row("Instance id", str(record.get("instance_id") or "")),
        _row("Agent name", str(record.get("agent_name") or "")),
        _row("Last updated", str(record.get("last_updated") or "—")),
        _row("Total runs", _format_int(record.get("total_runs", 0))),
        _row("Completed runs", _format_int(record.get("completed_runs", 0))),
        _row("Paused runs", _format_int(record.get("paused_runs", 0))),
        _row("Error runs", _format_int(record.get("error_runs", 0))),
        _row("Max cycles reached", _format_int(record.get("max_cycles_reached_runs", 0))),
        _row("Total sessions", _format_int(record.get("total_sessions", 0))),
        _row("Lifetime tokens (estimated)", _format_int(record.get("lifetime_tokens_estimated", 0))),
        _row("Lifetime tokens (actual)", _format_optional_int(record.get("lifetime_tokens_actual"))),
        _row("Avg resets / run", _format_decimal(record.get("avg_resets_per_run", 0.0))),
        _row("Avg cycles / run", _format_decimal(record.get("avg_cycles_per_run", 0.0))),
        _row("Avg duration / run", _format_duration(record.get("avg_duration_per_run", 0.0))),
    ]
    return "\n".join(lines)


def _render_rebuild_result(result: StatsRebuildResult) -> str:
    return "\n".join(
        [
            "harnessiq stats rebuild",
            "",
            "Stats rebuild complete",
            _row("Entries processed", _format_int(result.entries_processed)),
            _row("Entries applied", _format_int(result.entries_applied)),
            _row("Entries skipped", _format_int(result.entries_skipped)),
            _row("Ledger path", result.ledger_path),
            _row("Stats dir", result.stats_dir),
        ]
    )


def _row(label: str, value: str) -> str:
    return f"{label:<24} {value}"


def _format_decimal(value: Any) -> str:
    return f"{float(value):.1f}"


def _format_duration(value: Any) -> str:
    return f"{float(value):.1f} s"


def _format_int(value: Any) -> str:
    return f"{int(value):,}"


def _format_joined(value: Any) -> str:
    if isinstance(value, list):
        items = [str(item) for item in value if str(item).strip()]
        return ", ".join(items) if items else "—"
    return str(value) if value else "—"


def _format_optional_int(value: Any) -> str:
    if value is None:
        return "—"
    return _format_int(value)


def _format_percent(value: Any) -> str:
    return f"{float(value) * 100:.1f}%"


def _print_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 0


__all__ = ["register_stats_commands"]
