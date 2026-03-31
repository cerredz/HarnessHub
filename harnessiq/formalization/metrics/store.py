"""
===============================================================================
File: harnessiq/formalization/metrics/store.py

What this file does:
- Implements MetricStore, a durable disk-backed JSON store for metric values.
- All metric reads and writes go through this object so values survive context
  window resets (which clear the transcript but not disk state).

Use cases:
- Used internally by MetricsLayer. Not intended for direct use by agent code.

How to use it:
- Construct with a memory_path (Path). Reads existing values on init.
  Call get/set/apply_aggregation to read and update values.

Intent:
- Keep metric durability simple and explicit — one JSON file, no external
  dependencies, human-readable on disk.
===============================================================================
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_STORE_FILENAME = "metrics_store.json"


class MetricStore:
    """Durable disk-backed storage for metric values.

    All reads and writes go through this object. Metrics always survive
    context window resets because the store is on disk, not in the transcript.
    """

    def __init__(self, memory_path: Path) -> None:
        self._path = memory_path / _STORE_FILENAME
        self._cache: dict[str, Any] = self._load()

    def get(self, name: str, default: Any) -> Any:
        """Return the current value for name, or default if not yet set."""
        return self._cache.get(name, default)

    def set(self, name: str, value: Any) -> None:
        """Set a metric value directly, flushing to disk."""
        self._cache[name] = value
        self._flush()

    def apply_aggregation(
        self,
        name: str,
        new_value: Any,
        aggregation: str,
        initial: Any,
    ) -> Any:
        """Apply an aggregation rule and return the updated value."""
        current = self._cache.get(name, initial)
        if aggregation == "increment":
            updated = (current or 0) + new_value
        elif aggregation in ("set", "last"):
            updated = new_value
        elif aggregation == "max":
            updated = max(current, new_value)
        elif aggregation == "min":
            updated = min(current, new_value) if current is not None else new_value
        else:
            updated = new_value
        self._cache[name] = updated
        self._flush()
        return updated

    def all(self) -> dict[str, Any]:
        """Return a snapshot of all stored metric values."""
        return dict(self._cache)

    def _load(self) -> dict[str, Any]:
        if self._path.exists():
            raw = self._path.read_text(encoding="utf-8").strip()
            if raw:
                return json.loads(raw)
        return {}

    def _flush(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._cache, indent=2, default=str),
            encoding="utf-8",
        )
