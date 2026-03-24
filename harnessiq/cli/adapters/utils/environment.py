"""Environment-variable helpers for adapter runtime setup."""

from __future__ import annotations

import os
from pathlib import Path


def set_env_path_if_missing(
    variable_name: str,
    path: Path,
    *,
    require_existing: bool = False,
) -> None:
    """Populate one env var with a resolved path when the runtime expects a stable session directory."""
    if require_existing and not path.exists():
        return
    if variable_name not in os.environ:
        os.environ[variable_name] = str(path.resolve())


__all__ = ["set_env_path_if_missing"]
