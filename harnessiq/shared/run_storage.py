"""Shared run-storage contracts and default filesystem implementation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

RUNS_DIRNAME = "runs"


@dataclass(slots=True)
class RunRecord:
    """A generic persisted agent run record."""

    run_id: str
    started_at: str
    metadata: dict[str, Any]
    events: list[dict[str, Any]] = field(default_factory=list)
    completed_at: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "metadata": dict(self.metadata),
            "events": list(self.events),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunRecord":
        return cls(
            run_id=str(data["run_id"]),
            started_at=str(data["started_at"]),
            metadata=dict(data.get("metadata", {})),
            events=list(data.get("events", [])),
            completed_at=str(data["completed_at"]) if data.get("completed_at") else None,
        )


@runtime_checkable
class StorageBackend(Protocol):
    """Pluggable persistence layer for agent run tracking."""

    def start_run(self, run_id: str, metadata: dict[str, Any]) -> None:
        ...

    def finish_run(self, run_id: str, completed_at: str) -> None:
        ...

    def log_event(self, run_id: str, event_type: str, data: dict[str, Any]) -> None:
        ...

    def has_seen(self, key: str, value: str, *, event_type: str | None = None) -> bool:
        ...

    def current_run_id(self) -> str | None:
        ...


class FileSystemStorageBackend:
    """Default :class:`StorageBackend` that writes ``<run_id>.json`` files to disk."""

    def __init__(self, memory_path: Path) -> None:
        self._memory_path = Path(memory_path)
        self._runs_dir = self._memory_path / RUNS_DIRNAME
        self._current_run_id: str | None = None

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

    def _run_path(self, run_id: str) -> Path:
        return self._runs_dir / f"{run_id}.json"

    def _read_record(self, path: Path) -> RunRecord:
        data = json.loads(path.read_text(encoding="utf-8"))
        return RunRecord.from_dict(data)

    def _list_run_paths(self) -> list[Path]:
        paths = list(self._runs_dir.glob("run_*.json"))
        return sorted(paths, key=_run_file_sort_key)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _run_file_sort_key(path: Path) -> int:
    match = re.search(r"run_(\d+)\.json$", path.name)
    return int(match.group(1)) if match else 0


__all__ = [
    "FileSystemStorageBackend",
    "RunRecord",
    "RUNS_DIRNAME",
    "StorageBackend",
]
