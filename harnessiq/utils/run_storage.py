"""Compatibility facade for shared run-storage helpers."""

from __future__ import annotations

from harnessiq.shared.run_storage import (
    RUNS_DIRNAME,
    FileSystemStorageBackend,
    RunRecord,
    StorageBackend,
)

__all__ = [
    "FileSystemStorageBackend",
    "RunRecord",
    "RUNS_DIRNAME",
    "StorageBackend",
]
