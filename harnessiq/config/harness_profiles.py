"""Generic persisted harness-profile config for the platform-first CLI."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

DEFAULT_HARNESS_PROFILE_FILENAME = ".harnessiq-profile.json"


def build_harness_credential_binding_name(*, manifest_id: str, agent_name: str) -> str:
    """Return the deterministic credential-binding key for one harness profile."""
    normalized_manifest_id = manifest_id.strip()
    normalized_agent_name = agent_name.strip()
    if not normalized_manifest_id:
        raise ValueError("manifest_id must not be blank.")
    if not normalized_agent_name:
        raise ValueError("agent_name must not be blank.")
    return f"harness::{normalized_manifest_id}::{normalized_agent_name}"


@dataclass(frozen=True, slots=True)
class HarnessProfile:
    """Persisted runtime/custom parameter config for one harness memory folder."""

    manifest_id: str
    agent_name: str
    runtime_parameters: dict[str, Any] | None = None
    custom_parameters: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        normalized_manifest_id = self.manifest_id.strip()
        normalized_agent_name = self.agent_name.strip()
        if not normalized_manifest_id:
            raise ValueError("manifest_id must not be blank.")
        if not normalized_agent_name:
            raise ValueError("agent_name must not be blank.")
        object.__setattr__(self, "manifest_id", normalized_manifest_id)
        object.__setattr__(self, "agent_name", normalized_agent_name)
        object.__setattr__(self, "runtime_parameters", dict(self.runtime_parameters or {}))
        object.__setattr__(self, "custom_parameters", dict(self.custom_parameters or {}))

    @property
    def credential_binding_name(self) -> str:
        return build_harness_credential_binding_name(
            manifest_id=self.manifest_id,
            agent_name=self.agent_name,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "custom_parameters": dict(self.custom_parameters or {}),
            "manifest_id": self.manifest_id,
            "runtime_parameters": dict(self.runtime_parameters or {}),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "HarnessProfile":
        runtime_parameters = payload.get("runtime_parameters", {})
        custom_parameters = payload.get("custom_parameters", {})
        if not isinstance(runtime_parameters, dict):
            raise ValueError("Harness profile 'runtime_parameters' must be a JSON object.")
        if not isinstance(custom_parameters, dict):
            raise ValueError("Harness profile 'custom_parameters' must be a JSON object.")
        return cls(
            manifest_id=str(payload["manifest_id"]),
            agent_name=str(payload["agent_name"]),
            runtime_parameters=dict(runtime_parameters),
            custom_parameters=dict(custom_parameters),
        )


@dataclass(slots=True)
class HarnessProfileStore:
    """Read and write the generic harness-profile file inside a memory folder."""

    memory_path: Path | str

    def __post_init__(self) -> None:
        self.memory_path = Path(self.memory_path)

    @property
    def profile_path(self) -> Path:
        return self.memory_path / DEFAULT_HARNESS_PROFILE_FILENAME

    def load(self, *, manifest_id: str, agent_name: str) -> HarnessProfile:
        if not self.profile_path.exists():
            return HarnessProfile(manifest_id=manifest_id, agent_name=agent_name)
        raw = self.profile_path.read_text(encoding="utf-8").strip()
        if not raw:
            return HarnessProfile(manifest_id=manifest_id, agent_name=agent_name)
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("Harness profile file must contain a JSON object.")
        profile = HarnessProfile.from_dict(payload)
        if profile.manifest_id != manifest_id:
            raise ValueError(
                f"Harness profile '{self.profile_path}' belongs to manifest '{profile.manifest_id}', not '{manifest_id}'."
            )
        if profile.agent_name != agent_name:
            raise ValueError(
                f"Harness profile '{self.profile_path}' belongs to agent '{profile.agent_name}', not '{agent_name}'."
            )
        return profile

    def save(self, profile: HarnessProfile) -> Path:
        self.memory_path.mkdir(parents=True, exist_ok=True)
        self.profile_path.write_text(
            json.dumps(profile.as_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return self.profile_path

    def update(
        self,
        *,
        manifest_id: str,
        agent_name: str,
        runtime_parameters: Mapping[str, Any] | None = None,
        custom_parameters: Mapping[str, Any] | None = None,
    ) -> HarnessProfile:
        current = self.load(manifest_id=manifest_id, agent_name=agent_name)
        next_profile = HarnessProfile(
            manifest_id=manifest_id,
            agent_name=agent_name,
            runtime_parameters=(
                dict(runtime_parameters)
                if runtime_parameters is not None
                else current.runtime_parameters
            ),
            custom_parameters=(
                dict(custom_parameters)
                if custom_parameters is not None
                else current.custom_parameters
            ),
        )
        self.save(next_profile)
        return next_profile


__all__ = [
    "DEFAULT_HARNESS_PROFILE_FILENAME",
    "HarnessProfile",
    "HarnessProfileStore",
    "build_harness_credential_binding_name",
]
