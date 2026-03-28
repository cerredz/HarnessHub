"""Public SDK wrappers over persisted config and environment lifecycle helpers."""

from __future__ import annotations

import os
from pathlib import Path

from harnessiq.config.credentials import DotEnvFileNotFoundError, parse_dotenv_file
from harnessiq.config.credentials import CredentialsConfigStore, AgentCredentialsNotConfiguredError
from harnessiq.config.harness_profiles import build_harness_credential_binding_name
from harnessiq.shared.langsmith import LANGSMITH_ENV_ALIAS_GROUPS
from harnessiq.shared.harness_manifest import HarnessManifest


def seed_environment(repo_root: str | Path = ".") -> dict[str, str]:
    """Seed repo-local environment variables and LangSmith aliases."""
    parsed = _load_repo_environment_values(repo_root)
    if not parsed:
        return {}
    applied = _seed_environment_variables(parsed)
    applied.update(_seed_langsmith_aliases(parsed))
    return applied


def resolve_harness_credentials(
    manifest: HarnessManifest,
    *,
    agent_name: str,
    repo_root: str | Path = ".",
) -> dict[str, object]:
    """Resolve persisted credential bindings for one harness profile."""
    store = CredentialsConfigStore(repo_root=Path(repo_root))
    binding_name = build_harness_credential_binding_name(
        manifest_id=manifest.manifest_id,
        agent_name=agent_name,
    )
    try:
        binding = store.load().binding_for(binding_name)
    except AgentCredentialsNotConfiguredError:
        return {}
    resolved = store.resolve_binding(binding)
    resolved_by_family: dict[str, dict[str, str]] = {}
    for field_name, value in resolved.as_dict().items():
        family, _, credential_field = field_name.partition(".")
        if not credential_field:
            continue
        resolved_by_family.setdefault(family, {})[credential_field] = value
    credential_objects: dict[str, object] = {}
    for family, values in resolved_by_family.items():
        from harnessiq.config.provider_credentials.api import get_provider_credential_spec

        credential_objects[family] = get_provider_credential_spec(family).build_credentials(values)
    return credential_objects


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
            for path in (candidate / filename for filename in (".env", "local.env"))
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


__all__ = ["resolve_harness_credentials", "seed_environment"]
