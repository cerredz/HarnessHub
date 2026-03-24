"""CLI helpers for repo-local environment bootstrapping."""

from __future__ import annotations

import os
from pathlib import Path

from harnessiq.config import DotEnvFileNotFoundError, parse_dotenv_file
from harnessiq.shared.langsmith import LANGSMITH_ENV_ALIAS_GROUPS

_ENV_FILENAMES = (".env", "local.env")


def seed_cli_environment(repo_root: str | Path = ".") -> dict[str, str]:
    """Backfill repo-local env vars and LangSmith aliases for CLI run commands.

    The nearest directory containing either ``.env`` or ``local.env`` is used.
    When both files exist in that directory, ``local.env`` acts as an overlay on
    top of ``.env``. Existing process env vars remain authoritative.
    """
    parsed = _load_repo_environment_values(repo_root)
    if not parsed:
        return {}

    applied = _seed_environment_variables(parsed)
    applied.update(_seed_langsmith_aliases(parsed))
    return applied


def seed_langsmith_environment(repo_root: str | Path = ".") -> dict[str, str]:
    """Backfill LangSmith/LangChain tracing variables from repo-local env files."""
    parsed = _load_repo_environment_values(repo_root)
    if not parsed:
        return {}
    return _seed_langsmith_aliases(parsed)


def _load_repo_environment_values(repo_root: str | Path) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for env_path in _find_env_paths(repo_root):
        try:
            parsed.update(parse_dotenv_file(env_path))
        except DotEnvFileNotFoundError:
            continue
    return parsed


def _find_env_paths(repo_root: str | Path) -> tuple[Path, ...]:
    resolved_root = Path(repo_root).expanduser().resolve()
    for candidate in (resolved_root, *resolved_root.parents):
        env_paths = tuple(
            path
            for path in (candidate / filename for filename in _ENV_FILENAMES)
            if path.exists() and path.is_file()
        )
        if env_paths:
            return env_paths
    return ()


def _seed_environment_variables(parsed: dict[str, str]) -> dict[str, str]:
    applied: dict[str, str] = {}
    for env_name, value in parsed.items():
        if env_name in os.environ:
            continue
        os.environ[env_name] = value
        applied[env_name] = value
    return applied


def _seed_langsmith_aliases(parsed: dict[str, str]) -> dict[str, str]:
    applied: dict[str, str] = {}
    for canonical_name, legacy_name in LANGSMITH_ENV_ALIAS_GROUPS:
        resolved_value = parsed.get(canonical_name) or parsed.get(legacy_name)
        if resolved_value is None:
            continue
        for env_name in (canonical_name, legacy_name):
            if env_name in os.environ:
                continue
            os.environ[env_name] = resolved_value
            applied[env_name] = resolved_value
    return applied


__all__ = ["seed_cli_environment", "seed_langsmith_environment"]
