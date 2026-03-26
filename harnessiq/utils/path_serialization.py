"""Shared helpers for serializing repo-root-relative filesystem paths."""

from __future__ import annotations

from pathlib import Path


def serialize_repo_path(path: Path, *, repo_root: Path) -> str:
    resolved = path.expanduser()
    if not resolved.is_absolute():
        resolved = repo_root / resolved
    try:
        return resolved.relative_to(repo_root).as_posix()
    except ValueError:
        return resolved.as_posix()


def deserialize_repo_path(serialized: str, *, repo_root: Path) -> Path:
    candidate = Path(serialized)
    if candidate.is_absolute():
        return candidate
    return repo_root / candidate


__all__ = ["deserialize_repo_path", "serialize_repo_path"]
