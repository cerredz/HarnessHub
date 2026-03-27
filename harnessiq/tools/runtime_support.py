"""Shared local persistence helpers for stateful tool families."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_TOOL_RUNTIME_ROOT = Path("memory") / "_tool_runtime"


def resolve_runtime_root(root: str | Path | None = None) -> Path:
    target = Path(root) if root is not None else DEFAULT_TOOL_RUNTIME_ROOT
    target = target.expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    return target


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return default
    return json.loads(raw)


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return path


def append_jsonl(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, default=str))
        handle.write("\n")
    return path


__all__ = ["DEFAULT_TOOL_RUNTIME_ROOT", "append_jsonl", "read_json", "resolve_runtime_root", "utc_now", "write_json"]
