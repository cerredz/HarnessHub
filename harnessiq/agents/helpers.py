"""Shared helper utilities reused across agent packages."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from pathlib import Path


def find_repo_root(path: Path | None, *, memory_dir_name: str | None = None) -> Path:
    """Resolve the repository root for a memory path or return the CWD fallback."""
    if path is None:
        return Path.cwd()
    resolved = path.resolve()
    for candidate in (resolved, *resolved.parents):
        if (candidate / ".git").exists():
            return candidate
    if memory_dir_name and resolved.parent.name == memory_dir_name and resolved.parent.parent.name == "memory":
        return resolved.parent.parent.parent
    return Path.cwd()


def read_optional_text(path: Path) -> str:
    """Read a UTF-8 text file when it exists, otherwise return an empty string."""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def resolve_memory_path(
    memory_path: str | Path | None,
    *,
    default_path: Path,
    isolate_default: bool = False,
    default_subdir_prefix: str | None = None,
) -> Path:
    """Return the explicit memory path or a resolved default agent path."""
    if memory_path is None:
        if not isolate_default:
            return Path(default_path)
        return _build_isolated_memory_path(
            Path(default_path),
            prefix=default_subdir_prefix or Path(default_path).name,
        )
    return Path(memory_path)


def utc_now_z() -> str:
    """Return the current UTC timestamp in ISO-8601 Zulu format."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def utc_timestamp_for_filename() -> str:
    """Return a compact UTC timestamp suitable for filenames."""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _build_isolated_memory_path(default_path: Path, *, prefix: str) -> Path:
    normalized_prefix = "".join(
        character if character.isalnum() or character in {"-", "_"} else "-"
        for character in prefix.strip()
    ).strip("-") or "run"
    unique_suffix = secrets.token_hex(3)
    return default_path / f"{normalized_prefix}-{utc_timestamp_for_filename()}-{unique_suffix}"


__all__ = [
    "find_repo_root",
    "read_optional_text",
    "resolve_memory_path",
    "utc_now_z",
    "utc_timestamp_for_filename",
]
