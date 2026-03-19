"""CLI helpers for LangSmith environment bootstrapping."""

from __future__ import annotations

import os
from pathlib import Path

from harnessiq.config import DotEnvFileNotFoundError, parse_dotenv_file

_ENV_ALIAS_GROUPS = (
    ("LANGSMITH_API_KEY", "LANGCHAIN_API_KEY"),
    ("LANGSMITH_PROJECT", "LANGCHAIN_PROJECT"),
    ("LANGSMITH_ENDPOINT", "LANGCHAIN_ENDPOINT"),
    ("LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2"),
)


def seed_langsmith_environment(repo_root: str | Path = ".") -> dict[str, str]:
    """Backfill LangSmith/LangChain tracing variables from repo-local ``.env``."""
    env_path = _find_env_path(repo_root)
    if env_path is None:
        return {}
    try:
        parsed = parse_dotenv_file(env_path)
    except DotEnvFileNotFoundError:
        return {}

    applied: dict[str, str] = {}
    for canonical_name, legacy_name in _ENV_ALIAS_GROUPS:
        resolved_value = parsed.get(canonical_name) or parsed.get(legacy_name)
        if resolved_value is None:
            continue
        for env_name in (canonical_name, legacy_name):
            if env_name in os.environ:
                continue
            os.environ[env_name] = resolved_value
            applied[env_name] = resolved_value
    return applied


def _find_env_path(repo_root: str | Path) -> Path | None:
    resolved_root = Path(repo_root).expanduser().resolve()
    for candidate in (resolved_root, *resolved_root.parents):
        env_path = candidate / ".env"
        if env_path.exists() and env_path.is_file():
            return env_path
    return None


__all__ = ["seed_langsmith_environment"]
