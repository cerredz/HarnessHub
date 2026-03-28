"""Public SDK helpers and shared agent-construction utilities."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from harnessiq.config.harness_profiles import HarnessProfile, HarnessProfileStore
from harnessiq.config.provider_credentials.api import get_provider_credential_spec
from harnessiq.shared.agents import (
    DEFAULT_AGENT_MAX_TOKENS,
    DEFAULT_AGENT_RESET_THRESHOLD,
    AgentRuntimeConfig,
)
from harnessiq.shared.exceptions import ResourceNotFoundError
from harnessiq.shared.harness_manifest import HarnessManifest
from harnessiq.shared.harness_manifests import get_harness_manifest
from harnessiq.shared.hooks import DEFAULT_APPROVAL_POLICY
from harnessiq.shared.tool_selection import ToolSelectionConfig
from harnessiq.utils import ConnectionsConfigStore, build_output_sinks


def build_agent_runtime_config(
    *,
    sink_specs: Sequence[str] = (),
    use_persisted_connections: bool = True,
    approval_policy: str | None = None,
    allowed_tools: Sequence[str] = (),
    dynamic_tools_enabled: bool = False,
    dynamic_tool_top_k: int = 5,
    dynamic_tool_candidates: Sequence[str] = (),
    dynamic_tool_embedding_model: str | None = None,
    max_tokens: int = DEFAULT_AGENT_MAX_TOKENS,
    reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD,
    langsmith_tracing_enabled: bool = True,
    session_id: str | None = None,
) -> AgentRuntimeConfig:
    """Build an ``AgentRuntimeConfig`` from high-level SDK parameters."""
    output_sinks = ()
    if sink_specs:
        connections = ()
        if use_persisted_connections:
            connections = ConnectionsConfigStore().load().enabled_connections()
        output_sinks = build_output_sinks(connections=connections, sink_specs=sink_specs)
    tool_selection = ToolSelectionConfig(
        enabled=dynamic_tools_enabled,
        embedding_model=dynamic_tool_embedding_model,
        top_k=dynamic_tool_top_k,
        candidate_tool_keys=_parse_allowed_tool_values(dynamic_tool_candidates),
    )
    return AgentRuntimeConfig(
        max_tokens=max_tokens,
        reset_threshold=reset_threshold,
        approval_policy=approval_policy or DEFAULT_APPROVAL_POLICY,
        allowed_tools=_parse_allowed_tool_values(allowed_tools),
        tool_selection=tool_selection,
        output_sinks=output_sinks,
        langsmith_tracing_enabled=langsmith_tracing_enabled,
        session_id=session_id,
    )


def inspect_harness(manifest_id: str | HarnessManifest) -> dict[str, Any]:
    """Return the structured inspection payload for one harness manifest."""
    manifest = manifest_id if isinstance(manifest_id, HarnessManifest) else get_harness_manifest(manifest_id)
    return {
        "harness": manifest.manifest_id,
        "display_name": manifest.display_name,
        "import_path": manifest.import_path,
        "cli_command": manifest.cli_command,
        "cli_adapter_path": manifest.cli_adapter_path,
        "default_memory_root": manifest.resolved_default_memory_root,
        "runtime_parameters": [_render_parameter_spec(spec) for spec in manifest.runtime_parameters],
        "custom_parameters": [_render_parameter_spec(spec) for spec in manifest.custom_parameters],
        "runtime_parameters_open_ended": manifest.runtime_parameters_open_ended,
        "custom_parameters_open_ended": manifest.custom_parameters_open_ended,
        "memory_files": [
            {
                "key": entry.key,
                "relative_path": entry.relative_path,
                "description": entry.description,
                "kind": entry.kind,
                "format": entry.format,
            }
            for entry in manifest.memory_files
        ],
        "provider_families": list(manifest.provider_families),
        "provider_credential_fields": _build_provider_credential_fields(manifest),
        "output_schema": manifest.output_schema,
    }


def load_persisted_profile(
    *,
    manifest_id: str,
    memory_path: str | Path,
) -> HarnessProfile | None:
    """Load a persisted profile from ``memory_path`` when one exists."""
    store = HarnessProfileStore(memory_path=Path(memory_path))
    if not store.profile_path.exists():
        return None
    payload = json.loads(store.profile_path.read_text(encoding="utf-8"))
    profile = HarnessProfile.from_dict(payload)
    if profile.manifest_id != manifest_id:
        return None
    return profile


def merge_profile_parameters(
    *,
    profile: HarnessProfile | None,
    runtime_overrides: Mapping[str, Any] | None = None,
    custom_overrides: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Overlay explicit overrides on top of persisted profile parameters."""
    runtime_parameters = dict(profile.runtime_parameters if profile is not None else {})
    if runtime_overrides:
        runtime_parameters.update(runtime_overrides)
    custom_parameters = dict(profile.custom_parameters if profile is not None else {})
    if custom_overrides:
        custom_parameters.update(custom_overrides)
    return runtime_parameters, custom_parameters


def resolve_profile_memory_path(
    *,
    profile: HarnessProfile,
    manifest: HarnessManifest,
    memory_path: str | Path | None = None,
) -> Path:
    """Resolve the profile memory path, defaulting to the manifest root plus agent name."""
    if memory_path is not None:
        return Path(memory_path)
    return _resolve_memory_path(
        profile.agent_name,
        manifest.resolved_default_memory_root,
        slugifier=_slugify_agent_name,
    )


def load_master_prompt_text(
    *,
    default_path: Path,
    override: str | Path | None = None,
    missing_message: str,
) -> str:
    """Return prompt text from ``override`` or ``default_path``."""
    if override is not None:
        if isinstance(override, Path):
            if not override.exists():
                raise ResourceNotFoundError(missing_message)
            return override.read_text(encoding="utf-8")
        override_text = str(override)
        candidate_path = Path(override_text)
        if "\n" not in override_text and candidate_path.exists() and candidate_path.is_file():
            return candidate_path.read_text(encoding="utf-8")
        return override_text
    if not default_path.exists():
        raise ResourceNotFoundError(missing_message)
    return default_path.read_text(encoding="utf-8")


def _parse_allowed_tool_values(values: Sequence[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_value in values:
        for part in str(raw_value).split(","):
            candidate = part.strip()
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            normalized.append(candidate)
    return tuple(normalized)


def _slugify_agent_name(agent_name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", agent_name.strip()).strip("-")
    if not cleaned:
        raise ValueError("Agent names must contain at least one alphanumeric character.")
    return cleaned


def _resolve_memory_path(
    agent_name: str,
    memory_root: str,
    *,
    slugifier=_slugify_agent_name,
) -> Path:
    return Path(memory_root).expanduser() / slugifier(agent_name)


def _render_parameter_spec(spec) -> dict[str, Any]:
    return {
        "key": spec.key,
        "type": spec.value_type,
        "description": spec.description,
        "nullable": spec.nullable,
        "default": spec.default,
        "choices": list(spec.choices),
    }


def _build_provider_credential_fields(manifest: HarnessManifest) -> dict[str, list[dict[str, str]]]:
    credential_fields: dict[str, list[dict[str, str]]] = {}
    for family in manifest.provider_families:
        try:
            spec = get_provider_credential_spec(family)
        except KeyError:
            credential_fields[family] = []
            continue
        credential_fields[family] = [
            {
                "name": field.name,
                "description": field.description,
            }
            for field in spec.fields
        ]
    return credential_fields


__all__ = [
    "build_agent_runtime_config",
    "inspect_harness",
    "load_master_prompt_text",
    "load_persisted_profile",
    "merge_profile_parameters",
    "resolve_profile_memory_path",
]
