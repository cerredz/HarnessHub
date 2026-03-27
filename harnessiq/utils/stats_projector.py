"""Materialized stats views reconstructed from the append-only JSONL ledger."""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any, Mapping

from harnessiq.utils.ledger_connections import default_ledger_path
from harnessiq.utils.ledger_exports import load_ledger_entries
from harnessiq.utils.ledger_models import LedgerEntry

logger = logging.getLogger("harnessiq.stats")

STATS_SCHEMA_VERSION = 1
STATS_DIRNAME = "stats"
STATS_SNAPSHOT_NAMES = ("agents", "instances", "sessions", "daily")


@dataclass(frozen=True, slots=True)
class StatsRebuildResult:
    """Summary of a full stats rebuild run."""

    entries_processed: int
    entries_applied: int
    entries_skipped: int
    ledger_path: str
    stats_dir: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "entries_applied": self.entries_applied,
            "entries_processed": self.entries_processed,
            "entries_skipped": self.entries_skipped,
            "ledger_path": self.ledger_path,
            "stats_dir": self.stats_dir,
        }


class StatsProjector:
    """Project immutable run stats blocks into read-optimized local snapshots."""

    def __init__(self, ledger_path: Path | str | None = None) -> None:
        self.ledger_path = _resolve_ledger_path(ledger_path)
        self.stats_dir = stats_dir_for_ledger_path(self.ledger_path)

    def apply_entry(self, entry: LedgerEntry) -> bool:
        """Incrementally apply one ledger entry to the snapshot set."""
        stats = extract_entry_stats(entry)
        if stats is None:
            logger.warning(
                "Skipping stats projection for run %s because metadata.stats is missing or invalid.",
                entry.run_id,
            )
            return False
        snapshots = load_stats_snapshots(self.ledger_path)
        try:
            _apply_entry_to_snapshots(entry, stats, snapshots)
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Skipping malformed stats block for run %s: %s", entry.run_id, exc)
            return False
        write_stats_snapshots(snapshots, ledger_path=self.ledger_path)
        return True

    def rebuild(self) -> StatsRebuildResult:
        """Rebuild every snapshot by streaming the ledger from the beginning."""
        snapshots = _empty_stats_snapshots()
        processed = 0
        applied = 0
        skipped = 0
        for entry in load_ledger_entries(self.ledger_path):
            processed += 1
            stats = extract_entry_stats(entry)
            if stats is None:
                skipped += 1
                continue
            try:
                _apply_entry_to_snapshots(entry, stats, snapshots)
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("Skipping malformed stats block for run %s: %s", entry.run_id, exc)
                skipped += 1
                continue
            applied += 1
        write_stats_snapshots(snapshots, ledger_path=self.ledger_path)
        return StatsRebuildResult(
            entries_processed=processed,
            entries_applied=applied,
            entries_skipped=skipped,
            ledger_path=str(self.ledger_path),
            stats_dir=str(self.stats_dir),
        )


def stats_dir_for_ledger_path(ledger_path: Path | str | None = None) -> Path:
    """Return the stats directory colocated with the authoritative ledger."""
    resolved_ledger_path = _resolve_ledger_path(ledger_path)
    return resolved_ledger_path.parent / STATS_DIRNAME


def stats_snapshot_paths(ledger_path: Path | str | None = None) -> dict[str, Path]:
    """Return the absolute paths for every materialized stats snapshot file."""
    stats_dir = stats_dir_for_ledger_path(ledger_path)
    return {
        "agents": stats_dir / "agents.json",
        "instances": stats_dir / "instances.json",
        "sessions": stats_dir / "sessions.json",
        "daily": stats_dir / "daily.json",
    }


def load_stats_snapshots(ledger_path: Path | str | None = None) -> dict[str, dict[str, Any]]:
    """Load the current snapshot set from disk, defaulting to empty datasets."""
    snapshots = _empty_stats_snapshots()
    for name, path in stats_snapshot_paths(ledger_path).items():
        snapshots[name] = _load_snapshot_file(path)
    return snapshots


def write_stats_snapshots(
    snapshots: Mapping[str, Mapping[str, Any]],
    *,
    ledger_path: Path | str | None = None,
) -> None:
    """Write every snapshot file atomically."""
    paths = stats_snapshot_paths(ledger_path)
    for name, path in paths.items():
        payload = dict(snapshots.get(name, {}))
        _write_json_atomic(path, payload)


def export_stats_json(ledger_path: Path | str | None = None) -> str:
    """Export the current snapshot bundle as nested JSON."""
    return json.dumps(load_stats_snapshots(ledger_path), indent=2, sort_keys=True)


def iter_stats_run_rows(ledger_path: Path | str | None = None) -> list[dict[str, Any]]:
    """Return flat per-run stats rows derived directly from the ledger."""
    rows: list[dict[str, Any]] = []
    for entry in load_ledger_entries(_resolve_ledger_path(ledger_path)):
        stats = extract_entry_stats(entry)
        if stats is None:
            continue
        token_usage = _mapping(stats.get("token_usage"))
        timing = _mapping(stats.get("timing"))
        counters = _mapping(stats.get("counters"))
        rows.append(
            {
                "run_id": entry.run_id,
                "agent_name": entry.agent_name,
                "repo_id": stats.get("repo_id"),
                "instance_id": stats.get("instance_id"),
                "session_id": stats.get("session_id"),
                "model_provider": stats.get("model_provider"),
                "model_name": stats.get("model_name"),
                "run_status": stats.get("run_status"),
                "run_started_at": timing.get("run_started_at"),
                "run_finished_at": timing.get("run_finished_at"),
                "duration_seconds": timing.get("duration_seconds"),
                "token_source": token_usage.get("source"),
                "request_estimated": token_usage.get("request_estimated"),
                "input_actual": token_usage.get("input_actual"),
                "output_actual": token_usage.get("output_actual"),
                "total_actual": token_usage.get("total_actual"),
                "cycles_completed": counters.get("cycles_completed"),
                "reset_count": counters.get("reset_count"),
                "tool_calls": counters.get("tool_calls"),
                "distinct_tools": counters.get("distinct_tools"),
                "tool_call_breakdown": json.dumps(
                    _mapping(counters.get("tool_call_breakdown")),
                    sort_keys=True,
                ),
            }
        )
    return rows


def export_stats_csv(ledger_path: Path | str | None = None) -> str:
    """Export flat per-run stats rows as CSV."""
    rows = iter_stats_run_rows(ledger_path)
    if not rows:
        return ""
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue().rstrip()


def build_stats_summary(ledger_path: Path | str | None = None) -> dict[str, Any]:
    """Build a repo-wide summary from the materialized snapshots."""
    snapshots = load_stats_snapshots(ledger_path)
    agents = snapshots["agents"]
    sessions = snapshots["sessions"]
    total_runs = sum(int(bucket.get("total_runs", 0)) for bucket in agents.values())
    total_sessions = len(sessions)
    completed_runs = sum(int(bucket.get("completed_runs", 0)) for bucket in agents.values())
    paused_runs = sum(int(bucket.get("paused_runs", 0)) for bucket in agents.values())
    error_runs = sum(int(bucket.get("error_runs", 0)) for bucket in agents.values())
    max_cycles_reached_runs = sum(int(bucket.get("max_cycles_reached_runs", 0)) for bucket in agents.values())
    weighted_reset_total = sum(
        float(bucket.get("avg_resets_per_run", 0.0)) * int(bucket.get("total_runs", 0))
        for bucket in agents.values()
    )
    weighted_cycle_total = sum(
        float(bucket.get("avg_cycles_per_run", 0.0)) * int(bucket.get("total_runs", 0))
        for bucket in agents.values()
    )
    weighted_duration_total = sum(
        float(bucket.get("avg_duration_per_run", 0.0)) * int(bucket.get("total_runs", 0))
        for bucket in agents.values()
    )
    estimated_tokens = sum(int(bucket.get("lifetime_tokens_estimated", 0)) for bucket in agents.values())
    actual_values = [
        int(bucket["lifetime_tokens_actual"])
        for bucket in agents.values()
        if bucket.get("lifetime_tokens_actual") is not None
    ]
    last_updated = _max_iso_timestamp(
        [
            str(bucket.get("last_updated"))
            for snapshot in snapshots.values()
            for bucket in snapshot.values()
            if isinstance(bucket, dict) and bucket.get("last_updated") is not None
        ]
    )
    return {
        "total_runs": total_runs,
        "total_sessions": total_sessions,
        "completed_runs": completed_runs,
        "paused_runs": paused_runs,
        "error_runs": error_runs,
        "max_cycles_reached_runs": max_cycles_reached_runs,
        "success_rate": (completed_runs / total_runs) if total_runs else 0.0,
        "tokens_estimated": estimated_tokens,
        "tokens_actual": sum(actual_values) if actual_values else None,
        "avg_resets_per_run": (weighted_reset_total / total_runs) if total_runs else 0.0,
        "avg_cycles_per_run": (weighted_cycle_total / total_runs) if total_runs else 0.0,
        "avg_duration_per_run": (weighted_duration_total / total_runs) if total_runs else 0.0,
        "agents_active": sorted(agents),
        "snapshot_last_updated": last_updated,
    }


def extract_entry_stats(entry: LedgerEntry) -> dict[str, Any] | None:
    """Return the validated stats payload from one ledger entry."""
    stats = entry.metadata.get("stats")
    if not isinstance(stats, dict):
        return None
    try:
        version = int(stats.get("version", -1))
    except (TypeError, ValueError):
        return None
    if version != STATS_SCHEMA_VERSION:
        return None
    return stats


def _apply_entry_to_snapshots(
    entry: LedgerEntry,
    stats: Mapping[str, Any],
    snapshots: dict[str, dict[str, Any]],
) -> None:
    session_id = str(stats["session_id"])
    instance_id = str(stats["instance_id"])
    agent_name = entry.agent_name
    run_status = str(stats.get("run_status") or entry.status)
    timing = _mapping(stats.get("timing"))
    counters = _mapping(stats.get("counters"))
    token_usage = _mapping(stats.get("token_usage"))
    estimated_tokens = int(token_usage.get("request_estimated") or 0)
    actual_tokens = _actual_token_total(token_usage)
    cycles_completed = int(counters.get("cycles_completed") or 0)
    reset_count = int(counters.get("reset_count") or 0)
    duration_seconds = float(timing.get("duration_seconds") or 0.0)
    tool_breakdown = {
        str(tool_key): int(total_calls)
        for tool_key, total_calls in _mapping(counters.get("tool_call_breakdown")).items()
    }
    is_new_session = session_id not in snapshots["sessions"]
    run_started_at = str(timing.get("run_started_at"))
    run_finished_at = str(timing.get("run_finished_at"))
    day_key = run_started_at[:10]

    _apply_session_snapshot(
        session_id=session_id,
        snapshots=snapshots,
        entry=entry,
        run_status=run_status,
        run_started_at=run_started_at,
        run_finished_at=run_finished_at,
        estimated_tokens=estimated_tokens,
        actual_tokens=actual_tokens,
        reset_count=reset_count,
        cycles_completed=cycles_completed,
    )
    _apply_agent_snapshot(
        agent_name=agent_name,
        snapshots=snapshots,
        run_status=run_status,
        estimated_tokens=estimated_tokens,
        actual_tokens=actual_tokens,
        reset_count=reset_count,
        cycles_completed=cycles_completed,
        duration_seconds=duration_seconds,
        tool_breakdown=tool_breakdown,
        run_finished_at=run_finished_at,
        is_new_session=is_new_session,
    )
    _apply_instance_snapshot(
        instance_id=instance_id,
        agent_name=agent_name,
        snapshots=snapshots,
        run_status=run_status,
        estimated_tokens=estimated_tokens,
        actual_tokens=actual_tokens,
        reset_count=reset_count,
        cycles_completed=cycles_completed,
        duration_seconds=duration_seconds,
        run_finished_at=run_finished_at,
        is_new_session=is_new_session,
    )
    _apply_daily_snapshot(
        day_key=day_key,
        agent_name=agent_name,
        snapshots=snapshots,
        run_status=run_status,
        estimated_tokens=estimated_tokens,
        actual_tokens=actual_tokens,
        run_finished_at=run_finished_at,
    )


def _apply_agent_snapshot(
    *,
    agent_name: str,
    snapshots: dict[str, dict[str, Any]],
    run_status: str,
    estimated_tokens: int,
    actual_tokens: int | None,
    reset_count: int,
    cycles_completed: int,
    duration_seconds: float,
    tool_breakdown: Mapping[str, int],
    run_finished_at: str,
    is_new_session: bool,
) -> None:
    bucket = snapshots["agents"].setdefault(
        agent_name,
        {
            "agent_name": agent_name,
            "last_updated": run_finished_at,
            "total_runs": 0,
            "completed_runs": 0,
            "paused_runs": 0,
            "error_runs": 0,
            "max_cycles_reached_runs": 0,
            "success_rate": 0.0,
            "total_sessions": 0,
            "lifetime_tokens_estimated": 0,
            "lifetime_tokens_actual": None,
            "avg_resets_per_run": 0.0,
            "avg_cycles_per_run": 0.0,
            "avg_duration_per_run": 0.0,
            "top_tools": [],
        },
    )
    previous_runs = int(bucket["total_runs"])
    bucket["total_runs"] = previous_runs + 1
    bucket["last_updated"] = run_finished_at
    status_key = f"{run_status}_runs"
    if status_key in bucket:
        bucket[status_key] = int(bucket[status_key]) + 1
    if is_new_session:
        bucket["total_sessions"] = int(bucket["total_sessions"]) + 1
    bucket["lifetime_tokens_estimated"] = int(bucket["lifetime_tokens_estimated"]) + estimated_tokens
    bucket["lifetime_tokens_actual"] = _combine_optional_totals(bucket.get("lifetime_tokens_actual"), actual_tokens)
    bucket["avg_resets_per_run"] = _updated_average(
        float(bucket["avg_resets_per_run"]),
        previous_runs,
        reset_count,
    )
    bucket["avg_cycles_per_run"] = _updated_average(
        float(bucket["avg_cycles_per_run"]),
        previous_runs,
        cycles_completed,
    )
    bucket["avg_duration_per_run"] = _updated_average(
        float(bucket["avg_duration_per_run"]),
        previous_runs,
        duration_seconds,
    )
    bucket["success_rate"] = (
        int(bucket["completed_runs"]) / int(bucket["total_runs"])
        if int(bucket["total_runs"])
        else 0.0
    )
    bucket["top_tools"] = _merged_tool_totals(bucket.get("top_tools"), tool_breakdown)


def _apply_instance_snapshot(
    *,
    instance_id: str,
    agent_name: str,
    snapshots: dict[str, dict[str, Any]],
    run_status: str,
    estimated_tokens: int,
    actual_tokens: int | None,
    reset_count: int,
    cycles_completed: int,
    duration_seconds: float,
    run_finished_at: str,
    is_new_session: bool,
) -> None:
    bucket = snapshots["instances"].setdefault(
        instance_id,
        {
            "instance_id": instance_id,
            "agent_name": agent_name,
            "last_updated": run_finished_at,
            "total_runs": 0,
            "completed_runs": 0,
            "paused_runs": 0,
            "error_runs": 0,
            "max_cycles_reached_runs": 0,
            "total_sessions": 0,
            "lifetime_tokens_estimated": 0,
            "lifetime_tokens_actual": None,
            "avg_resets_per_run": 0.0,
            "avg_cycles_per_run": 0.0,
            "avg_duration_per_run": 0.0,
        },
    )
    previous_runs = int(bucket["total_runs"])
    bucket["agent_name"] = agent_name
    bucket["last_updated"] = run_finished_at
    bucket["total_runs"] = previous_runs + 1
    status_key = f"{run_status}_runs"
    if status_key in bucket:
        bucket[status_key] = int(bucket[status_key]) + 1
    if is_new_session:
        bucket["total_sessions"] = int(bucket["total_sessions"]) + 1
    bucket["lifetime_tokens_estimated"] = int(bucket["lifetime_tokens_estimated"]) + estimated_tokens
    bucket["lifetime_tokens_actual"] = _combine_optional_totals(bucket.get("lifetime_tokens_actual"), actual_tokens)
    bucket["avg_resets_per_run"] = _updated_average(
        float(bucket["avg_resets_per_run"]),
        previous_runs,
        reset_count,
    )
    bucket["avg_cycles_per_run"] = _updated_average(
        float(bucket["avg_cycles_per_run"]),
        previous_runs,
        cycles_completed,
    )
    bucket["avg_duration_per_run"] = _updated_average(
        float(bucket["avg_duration_per_run"]),
        previous_runs,
        duration_seconds,
    )


def _apply_session_snapshot(
    *,
    session_id: str,
    snapshots: dict[str, dict[str, Any]],
    entry: LedgerEntry,
    run_status: str,
    run_started_at: str,
    run_finished_at: str,
    estimated_tokens: int,
    actual_tokens: int | None,
    reset_count: int,
    cycles_completed: int,
) -> None:
    bucket = snapshots["sessions"].setdefault(
        session_id,
        {
            "session_id": session_id,
            "instance_id": entry.metadata["stats"]["instance_id"],
            "agent_name": entry.agent_name,
            "run_ids": [],
            "run_count": 0,
            "session_status": run_status,
            "session_started_at": run_started_at,
            "session_finished_at": run_finished_at,
            "session_duration_seconds": 0.0,
            "session_tokens_estimated": 0,
            "session_tokens_actual": None,
            "pause_count": 0,
            "total_resets": 0,
            "total_cycles": 0,
            "last_updated": run_finished_at,
        },
    )
    bucket["instance_id"] = entry.metadata["stats"]["instance_id"]
    bucket["agent_name"] = entry.agent_name
    bucket["run_ids"] = list(bucket["run_ids"]) + [entry.run_id]
    bucket["run_count"] = int(bucket["run_count"]) + 1
    bucket["session_status"] = run_status
    bucket["session_started_at"] = _min_iso_timestamp(str(bucket["session_started_at"]), run_started_at)
    bucket["session_finished_at"] = _max_iso_timestamp([str(bucket["session_finished_at"]), run_finished_at])
    bucket["session_duration_seconds"] = _iso_duration_seconds(
        str(bucket["session_started_at"]),
        str(bucket["session_finished_at"]),
    )
    bucket["session_tokens_estimated"] = int(bucket["session_tokens_estimated"]) + estimated_tokens
    bucket["session_tokens_actual"] = _combine_optional_totals(bucket.get("session_tokens_actual"), actual_tokens)
    if run_status == "paused":
        bucket["pause_count"] = int(bucket["pause_count"]) + 1
    bucket["total_resets"] = int(bucket["total_resets"]) + reset_count
    bucket["total_cycles"] = int(bucket["total_cycles"]) + cycles_completed
    bucket["last_updated"] = run_finished_at


def _apply_daily_snapshot(
    *,
    day_key: str,
    agent_name: str,
    snapshots: dict[str, dict[str, Any]],
    run_status: str,
    estimated_tokens: int,
    actual_tokens: int | None,
    run_finished_at: str,
) -> None:
    bucket = snapshots["daily"].setdefault(
        day_key,
        {
            "date": day_key,
            "total_runs": 0,
            "completed_runs": 0,
            "paused_runs": 0,
            "error_runs": 0,
            "max_cycles_reached_runs": 0,
            "tokens_estimated": 0,
            "tokens_actual": None,
            "agents_active": [],
            "last_updated": run_finished_at,
        },
    )
    bucket["total_runs"] = int(bucket["total_runs"]) + 1
    status_key = f"{run_status}_runs"
    if status_key in bucket:
        bucket[status_key] = int(bucket[status_key]) + 1
    bucket["tokens_estimated"] = int(bucket["tokens_estimated"]) + estimated_tokens
    bucket["tokens_actual"] = _combine_optional_totals(bucket.get("tokens_actual"), actual_tokens)
    active_agents = set(bucket.get("agents_active", []))
    active_agents.add(agent_name)
    bucket["agents_active"] = sorted(active_agents)
    bucket["last_updated"] = run_finished_at


def _merged_tool_totals(existing_tools: Any, tool_breakdown: Mapping[str, int]) -> list[dict[str, Any]]:
    totals: dict[str, int] = {}
    for item in existing_tools if isinstance(existing_tools, list) else []:
        if not isinstance(item, Mapping):
            continue
        tool_key = str(item.get("tool_key", "")).strip()
        if not tool_key:
            continue
        totals[tool_key] = int(item.get("total_calls", 0))
    for tool_key, total_calls in tool_breakdown.items():
        totals[tool_key] = totals.get(tool_key, 0) + total_calls
    return [
        {"tool_key": tool_key, "total_calls": totals[tool_key]}
        for tool_key in sorted(totals, key=lambda key: (-totals[key], key))
    ]


def _updated_average(current_average: float, previous_count: int, new_value: float) -> float:
    if previous_count <= 0:
        return float(new_value)
    return ((current_average * previous_count) + float(new_value)) / (previous_count + 1)


def _combine_optional_totals(existing: Any, value: int | None) -> int | None:
    if value is None:
        return int(existing) if existing is not None else None
    if existing is None:
        return value
    return int(existing) + value


def _actual_token_total(token_usage: Mapping[str, Any]) -> int | None:
    if str(token_usage.get("source", "")).strip().lower() != "actual":
        return None
    total_actual = token_usage.get("total_actual")
    if total_actual is None:
        return None
    return int(total_actual)


def _load_snapshot_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Ignoring invalid stats snapshot at %s.", path)
        return {}
    if not isinstance(payload, dict):
        logger.warning("Ignoring non-object stats snapshot at %s.", path)
        return {}
    return payload


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.tmp")
    temp_path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True), encoding="utf-8")
    temp_path.replace(path)


def _resolve_ledger_path(ledger_path: Path | str | None) -> Path:
    if ledger_path is None:
        return default_ledger_path()
    return Path(ledger_path).expanduser()


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _parse_iso_datetime(text: str) -> float:
    normalized = text.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    return float(datetime.fromisoformat(normalized).astimezone(timezone.utc).timestamp())


def _min_iso_timestamp(left: str, right: str) -> str:
    return left if _parse_iso_datetime(left) <= _parse_iso_datetime(right) else right


def _max_iso_timestamp(values: list[str]) -> str | None:
    candidates = [value for value in values if value and value != "None"]
    if not candidates:
        return None
    return max(candidates, key=_parse_iso_datetime)


def _iso_duration_seconds(started_at: str, finished_at: str) -> float:
    return max(0.0, _parse_iso_datetime(finished_at) - _parse_iso_datetime(started_at))


def _empty_stats_snapshots() -> dict[str, dict[str, Any]]:
    return {name: {} for name in STATS_SNAPSHOT_NAMES}


__all__ = [
    "STATS_DIRNAME",
    "STATS_SCHEMA_VERSION",
    "STATS_SNAPSHOT_NAMES",
    "StatsProjector",
    "StatsRebuildResult",
    "build_stats_summary",
    "export_stats_csv",
    "export_stats_json",
    "extract_entry_stats",
    "iter_stats_run_rows",
    "load_stats_snapshots",
    "stats_dir_for_ledger_path",
    "stats_snapshot_paths",
    "write_stats_snapshots",
]
