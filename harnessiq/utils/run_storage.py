"""Agent-agnostic run storage: StorageBackend protocol and FileSystemStorageBackend.

These components can be used by any agent that needs to persist run data over time.
``StorageBackend`` is a ``@runtime_checkable`` Protocol, so custom implementations
can route persistence to any backend (database, spreadsheet, CRM, etc.) without
inheriting from a base class.

The default implementation is :class:`FileSystemStorageBackend`, which writes one
JSON file per run under ``memory_path/runs/<run_id>.json``.  Each file stores a
:class:`RunRecord` — a run-id, timestamps, free-form metadata, and a typed event
log — so any agent can append its own event types without touching this module.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RUNS_DIRNAME = "runs"

# ---------------------------------------------------------------------------
# RunRecord
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class RunRecord:
    """A generic persisted agent run record.

    Attributes:
        run_id: Unique identifier for this run (e.g. ``run_1``).
        started_at: ISO-8601 UTC timestamp set when the run begins.
        metadata: Free-form run-level data supplied by the agent (e.g. the search
            query, model name, or any other per-run context).
        events: Ordered list of typed event dicts appended during the run.  Each
            entry has the shape ``{"type": "<event_type>", "data": {...}}``.
        completed_at: ISO-8601 UTC timestamp set when the run finishes, or
            ``None`` if the run is still in progress.
    """

    run_id: str
    started_at: str
    metadata: dict[str, Any]
    events: list[dict[str, Any]] = field(default_factory=list)
    completed_at: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "metadata": dict(self.metadata),
            "events": list(self.events),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunRecord":
        """Construct a :class:`RunRecord` from a raw dict (e.g. parsed from JSON)."""
        return cls(
            run_id=str(data["run_id"]),
            started_at=str(data["started_at"]),
            metadata=dict(data.get("metadata", {})),
            events=list(data.get("events", [])),
            completed_at=str(data["completed_at"]) if data.get("completed_at") else None,
        )


# ---------------------------------------------------------------------------
# StorageBackend protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class StorageBackend(Protocol):
    """Pluggable persistence layer for agent run tracking.

    The default implementation is :class:`FileSystemStorageBackend`.
    Custom implementations can route to any backend (database, spreadsheet,
    CRM, etc.) by implementing this protocol.
    """

    def start_run(self, run_id: str, metadata: dict[str, Any]) -> None:
        """Initialise storage for a new run before the agent loop starts."""
        ...

    def finish_run(self, run_id: str, completed_at: str) -> None:
        """Mark a run as complete after the agent loop exits."""
        ...

    def log_event(self, run_id: str, event_type: str, data: dict[str, Any]) -> None:
        """Append a typed event record to the run.

        Called deterministically inside tool handlers so every significant
        agent action is persisted regardless of LLM behaviour.

        Args:
            run_id: The active run identifier.
            event_type: A short, dot-free string identifying the event kind
                (e.g. ``"lead"``, ``"email_sent"``).
            data: A JSON-serialisable dict of event-specific fields.
        """
        ...

    def has_seen(self, key: str, value: str, *, event_type: str | None = None) -> bool:
        """Return ``True`` if any prior event has ``data[key] == value``.

        Scans all existing run files.  Pass ``event_type`` to restrict the
        search to events of a specific type (e.g. ``event_type="lead"``).
        """
        ...

    def current_run_id(self) -> str | None:
        """Return the active run ID, or ``None`` if no run has been started."""
        ...


# ---------------------------------------------------------------------------
# FileSystemStorageBackend
# ---------------------------------------------------------------------------


class FileSystemStorageBackend:
    """Default :class:`StorageBackend` that writes ``<run_id>.json`` files to disk.

    Each run gets its own file under ``memory_path/runs/<run_id>.json``.
    ``has_seen`` scans all existing run files for a matching key-value pair
    inside the event log, optionally filtered by event type.
    """

    def __init__(self, memory_path: Path) -> None:
        self._memory_path = Path(memory_path)
        self._runs_dir = self._memory_path / RUNS_DIRNAME
        self._current_run_id: str | None = None

    # ------------------------------------------------------------------
    # StorageBackend implementation
    # ------------------------------------------------------------------

    def start_run(self, run_id: str, metadata: dict[str, Any]) -> None:
        self._runs_dir.mkdir(parents=True, exist_ok=True)
        self._current_run_id = run_id
        record = RunRecord(run_id=run_id, started_at=_utcnow(), metadata=dict(metadata))
        _write_json(self._run_path(run_id), record.as_dict())

    def finish_run(self, run_id: str, completed_at: str) -> None:
        path = self._run_path(run_id)
        record = self._read_record(path)
        record.completed_at = completed_at
        _write_json(path, record.as_dict())

    def log_event(self, run_id: str, event_type: str, data: dict[str, Any]) -> None:
        path = self._run_path(run_id)
        record = self._read_record(path)
        record.events.append({"type": event_type, "data": dict(data)})
        _write_json(path, record.as_dict())

    def has_seen(self, key: str, value: str, *, event_type: str | None = None) -> bool:
        if not self._runs_dir.exists():
            return False
        for run_path in self._list_run_paths():
            try:
                record = self._read_record(run_path)
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
            for event in record.events:
                if event_type is not None and event.get("type") != event_type:
                    continue
                if str(event.get("data", {}).get(key, "")) == str(value):
                    return True
        return False

    def current_run_id(self) -> str | None:
        return self._current_run_id

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_path(self, run_id: str) -> Path:
        return self._runs_dir / f"{run_id}.json"

    def _read_record(self, path: Path) -> RunRecord:
        data = json.loads(path.read_text(encoding="utf-8"))
        return RunRecord.from_dict(data)

    def _list_run_paths(self) -> list[Path]:
        """Return run JSON files sorted by run number ascending."""
        paths = list(self._runs_dir.glob("run_*.json"))
        return sorted(paths, key=_run_file_sort_key)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _run_file_sort_key(path: Path) -> int:
    """Extract the run number from ``run_N.json`` for deterministic sorting."""
    match = re.search(r"run_(\d+)\.json$", path.name)
    return int(match.group(1)) if match else 0


__all__ = [
    "FileSystemStorageBackend",
    "RunRecord",
    "RUNS_DIRNAME",
    "StorageBackend",
]
