"""JSON-safe payload helpers for platform CLI adapter responses."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json_object(path: Path) -> dict[str, Any]:
    """Load a JSON object file into a mutable dict while tolerating missing or blank files."""
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in '{path.name}'.")
    return dict(payload)


def optional_string(value: Any) -> str | None:
    """Return a value only when it is a non-empty string so JSON payloads stay explicit."""
    return value if isinstance(value, str) and value else None


def result_payload(result: Any) -> dict[str, Any]:
    """Project the common run-result fields adapters expose in CLI JSON output."""
    return {
        "cycles_completed": getattr(result, "cycles_completed", None),
        "pause_reason": getattr(result, "pause_reason", None),
        "resets": getattr(result, "resets", None),
        "status": getattr(result, "status", None),
    }


__all__ = [
    "optional_string",
    "read_json_object",
    "result_payload",
]
