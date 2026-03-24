"""Ledger loading, filtering, export, and follow helpers."""

from __future__ import annotations

import csv
import json
import os
import time
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any, Mapping, Sequence

from harnessiq.shared.instagram import INSTAGRAM_HARNESS_MANIFEST, build_instagram_lead_export_rows
from harnessiq.utils.ledger_connections import default_ledger_path
from harnessiq.utils.ledger_models import LedgerEntry, _isoformat_z, parse_relative_duration


def load_ledger_entries(path: Path | str | None = None) -> list[LedgerEntry]:
    ledger_path = Path(path).expanduser() if path is not None else default_ledger_path()
    if not ledger_path.exists():
        return []
    entries: list[LedgerEntry] = []
    for raw_line in ledger_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            entries.append(LedgerEntry.from_dict(payload))
    return sorted(entries, key=lambda entry: entry.finished_at)


def filter_ledger_entries(
    entries: Sequence[LedgerEntry],
    *,
    agent_name: str | None = None,
    since: str | None = None,
) -> list[LedgerEntry]:
    filtered = list(entries)
    if agent_name is not None:
        filtered = [entry for entry in filtered if entry.agent_name == agent_name]
    if since is not None:
        threshold = datetime.now(timezone.utc) - parse_relative_duration(since)
        filtered = [entry for entry in filtered if entry.finished_at >= threshold]
    return filtered


def export_ledger_entries(
    entries: Sequence[LedgerEntry],
    *,
    output_format: str,
    flatten_outputs: bool = False,
) -> str:
    normalized = output_format.strip().lower()
    if normalized == "json":
        return json.dumps([entry.as_dict() for entry in entries], indent=2, sort_keys=True)
    if normalized == "jsonl":
        return "\n".join(json.dumps(entry.as_dict(), sort_keys=True) for entry in entries)
    if normalized == "csv":
        return _export_entries_csv(entries, flatten_outputs=flatten_outputs)
    if normalized == "markdown":
        return _export_entries_markdown(entries, flatten_outputs=flatten_outputs)
    raise ValueError(f"Unsupported export format '{output_format}'.")


def follow_ledger(path: Path | str | None = None, *, poll_interval: float = 0.5) -> None:
    ledger_path = Path(path).expanduser() if path is not None else default_ledger_path()
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.touch(exist_ok=True)
    with ledger_path.open("r", encoding="utf-8") as handle:
        handle.seek(0, os.SEEK_END)
        while True:
            line = handle.readline()
            if line:
                print(line.rstrip())
                continue
            time.sleep(poll_interval)


def _export_entries_csv(entries: Sequence[LedgerEntry], *, flatten_outputs: bool) -> str:
    rows: list[dict[str, Any]] = []
    for entry in entries:
        rows.extend(_entry_to_rows(entry, flatten_outputs=flatten_outputs))
    if not rows:
        return ""
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue().rstrip()


def _export_entries_markdown(entries: Sequence[LedgerEntry], *, flatten_outputs: bool) -> str:
    lines = ["# Ledger Export", ""]
    for entry in entries:
        lines.append(f"## {entry.agent_name} - {entry.run_id}")
        lines.append(f"- Status: `{entry.status}`")
        lines.append(f"- Finished: `{_isoformat_z(entry.finished_at)}`")
        lines.append(f"- Resets: {entry.reset_count}")
        payload = _entry_to_row(entry, flatten_outputs=flatten_outputs)
        lines.append("```json")
        lines.append(json.dumps(payload, indent=2, sort_keys=True))
        lines.append("```")
        lines.append("")
    return "\n".join(lines).rstrip()


def _entry_to_rows(entry: LedgerEntry, *, flatten_outputs: bool) -> list[dict[str, Any]]:
    instagram_rows = _maybe_export_instagram_lead_rows(entry, flatten_outputs=flatten_outputs)
    if instagram_rows is not None:
        return instagram_rows
    return [_entry_to_row(entry, flatten_outputs=flatten_outputs)]


def _entry_to_row(entry: LedgerEntry, *, flatten_outputs: bool) -> dict[str, Any]:
    row: dict[str, Any] = {
        "agent_name": entry.agent_name,
        "finished_at": _isoformat_z(entry.finished_at),
        "reset_count": entry.reset_count,
        "run_id": entry.run_id,
        "started_at": _isoformat_z(entry.started_at),
        "status": entry.status,
        "tags": ",".join(entry.tags),
    }
    if flatten_outputs:
        row.update({f"outputs.{key}": value for key, value in _flatten_mapping(entry.outputs).items()})
        row.update({f"metadata.{key}": value for key, value in _flatten_mapping(entry.metadata).items()})
    else:
        row["outputs"] = json.dumps(entry.outputs, sort_keys=True)
        row["metadata"] = json.dumps(entry.metadata, sort_keys=True)
    return row


def _maybe_export_instagram_lead_rows(
    entry: LedgerEntry,
    *,
    flatten_outputs: bool,
) -> list[dict[str, Any]] | None:
    if not flatten_outputs or entry.agent_name != INSTAGRAM_HARNESS_MANIFEST.agent_name:
        return None
    leads = entry.outputs.get("leads")
    if not isinstance(leads, list):
        return None
    rows: list[dict[str, Any]] = []
    for lead in leads:
        if not isinstance(lead, Mapping):
            continue
        rows.extend(build_instagram_lead_export_rows(lead))
    return rows


def _flatten_mapping(payload: Mapping[str, Any], prefix: str = "") -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for key, value in payload.items():
        next_key = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, Mapping):
            flattened.update(_flatten_mapping(value, prefix=next_key))
            continue
        if isinstance(value, list):
            flattened[next_key] = json.dumps(value, sort_keys=True)
            continue
        flattened[next_key] = value
    return flattened


__all__ = [
    "export_ledger_entries",
    "filter_ledger_entries",
    "follow_ledger",
    "load_ledger_entries",
]
