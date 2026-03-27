"""JSON-safe payload helpers for platform CLI adapter responses."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from harnessiq.shared.dtos import HarnessRunResultDTO


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


def result_payload(result: Any) -> HarnessRunResultDTO:
    """Project the common run-result fields adapters expose in CLI JSON output."""
    return HarnessRunResultDTO.from_result(result)


__all__ = [
    "optional_string",
    "read_json_object",
    "result_payload",
]
