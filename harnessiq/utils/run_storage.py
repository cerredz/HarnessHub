"""Compatibility facade for shared run-storage primitives."""

from __future__ import annotations

from harnessiq.shared.run_storage import (
    FileSystemStorageBackend,
    RUNS_DIRNAME,
    RunRecord,
    StorageBackend,
)

__all__ = [
    "FileSystemStorageBackend",
    "RunRecord",
    "RUNS_DIRNAME",
    "StorageBackend",
]
