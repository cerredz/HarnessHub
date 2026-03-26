"""Generic persisted harness-profile config for the platform-first CLI."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from harnessiq.utils.path_serialization import deserialize_repo_path, serialize_repo_path

DEFAULT_HARNESS_PROFILE_FILENAME = ".harnessiq-profile.json"
DEFAULT_HARNESS_PROFILE_INDEX_FILENAME = "harness_profiles.json"
DEFAULT_MEMORY_ROOT_DIRNAME = "memory"
_UNSET = object()


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
class HarnessRunSnapshot:
    """Persisted replay metadata for one platform-first run."""

    model_factory: str | None = None
    model_spec: str | None = None
    model_profile: str | None = None
    sink_specs: tuple[str, ...] = ()
    max_cycles: int | None = None
    adapter_arguments: dict[str, Any] | None = None
    runtime_parameters: dict[str, Any] | None = None
    custom_parameters: dict[str, Any] | None = None
    recorded_at: str | None = None
    run_number: int | None = None

    def __post_init__(self) -> None:
        normalized_model_factory = _normalize_optional_string(self.model_factory)
        normalized_model_spec = _normalize_optional_string(self.model_spec)
        normalized_model_profile = _normalize_optional_string(self.model_profile)
        selected_count = sum(
            1
            for value in (
                normalized_model_factory,
                normalized_model_spec,
                normalized_model_profile,
            )
            if value is not None
        )
        if selected_count != 1:
            raise ValueError("Exactly one of model_factory, model_spec, or model_profile must be provided.")
        object.__setattr__(self, "model_factory", normalized_model_factory)
        object.__setattr__(self, "model_spec", normalized_model_spec)
        object.__setattr__(self, "model_profile", normalized_model_profile)
        object.__setattr__(self, "sink_specs", tuple(str(spec) for spec in self.sink_specs))
        object.__setattr__(self, "adapter_arguments", dict(self.adapter_arguments or {}))
        object.__setattr__(self, "runtime_parameters", dict(self.runtime_parameters or {}))
        object.__setattr__(self, "custom_parameters", dict(self.custom_parameters or {}))
        object.__setattr__(self, "recorded_at", (self.recorded_at or _utcnow()).strip())
        if self.run_number is not None and self.run_number < 1:
            raise ValueError("run_number must be greater than or equal to 1 when present.")

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "adapter_arguments": dict(self.adapter_arguments or {}),
            "custom_parameters": dict(self.custom_parameters or {}),
            "max_cycles": self.max_cycles,
            "recorded_at": self.recorded_at,
            "runtime_parameters": dict(self.runtime_parameters or {}),
            "sink_specs": list(self.sink_specs),
        }
        if self.model_factory is not None:
            payload["model_factory"] = self.model_factory
        if self.model_spec is not None:
            payload["model_spec"] = self.model_spec
        if self.model_profile is not None:
            payload["model_profile"] = self.model_profile
        if self.run_number is not None:
            payload["run_number"] = self.run_number
        return payload

    def with_run_number(self, run_number: int) -> "HarnessRunSnapshot":
        return HarnessRunSnapshot(
            model_factory=self.model_factory,
            model_spec=self.model_spec,
            model_profile=self.model_profile,
            sink_specs=self.sink_specs,
            max_cycles=self.max_cycles,
            adapter_arguments=self.adapter_arguments,
            runtime_parameters=self.runtime_parameters,
            custom_parameters=self.custom_parameters,
            recorded_at=self.recorded_at,
            run_number=run_number,
        )

    @property
    def summary(self) -> dict[str, Any]:
        return {
            "recorded_at": self.recorded_at,
            "run_number": self.run_number,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "HarnessRunSnapshot":
        sink_specs = payload.get("sink_specs", ())
        adapter_arguments = payload.get("adapter_arguments", {})
        runtime_parameters = payload.get("runtime_parameters", {})
        custom_parameters = payload.get("custom_parameters", {})
        if not isinstance(sink_specs, (list, tuple)):
            raise ValueError("Harness run snapshot 'sink_specs' must be a JSON array.")
        if not isinstance(adapter_arguments, dict):
            raise ValueError("Harness run snapshot 'adapter_arguments' must be a JSON object.")
        if not isinstance(runtime_parameters, dict):
            raise ValueError("Harness run snapshot 'runtime_parameters' must be a JSON object.")
        if not isinstance(custom_parameters, dict):
            raise ValueError("Harness run snapshot 'custom_parameters' must be a JSON object.")
        max_cycles = payload.get("max_cycles")
        if max_cycles is not None and not isinstance(max_cycles, int):
            raise ValueError("Harness run snapshot 'max_cycles' must be an integer or null.")
        recorded_at = payload.get("recorded_at")
        if recorded_at is not None and not isinstance(recorded_at, str):
            raise ValueError("Harness run snapshot 'recorded_at' must be a string when present.")
        run_number = payload.get("run_number")
        if run_number is not None and not isinstance(run_number, int):
            raise ValueError("Harness run snapshot 'run_number' must be an integer when present.")
        return cls(
            model_factory=(
                str(payload["model_factory"])
                if payload.get("model_factory") is not None
                else None
            ),
            model_spec=(
                str(payload["model_spec"])
                if payload.get("model_spec") is not None
                else None
            ),
            model_profile=(
                str(payload["model_profile"])
                if payload.get("model_profile") is not None
                else None
            ),
            sink_specs=tuple(str(spec) for spec in sink_specs),
            max_cycles=max_cycles,
            adapter_arguments=dict(adapter_arguments),
            runtime_parameters=dict(runtime_parameters),
            custom_parameters=dict(custom_parameters),
            recorded_at=recorded_at,
            run_number=run_number,
        )


@dataclass(frozen=True, slots=True)
class HarnessProfile:
    """Persisted runtime/custom parameter config for one harness memory folder."""

    manifest_id: str
    agent_name: str
    runtime_parameters: dict[str, Any] | None = None
    custom_parameters: dict[str, Any] | None = None
    last_run: HarnessRunSnapshot | None = None
    run_history: tuple[HarnessRunSnapshot, ...] = ()

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
        normalized_history = _normalize_run_history(run_history=self.run_history, last_run=self.last_run)
        object.__setattr__(self, "run_history", normalized_history)
        object.__setattr__(self, "last_run", normalized_history[-1] if normalized_history else None)

    @property
    def credential_binding_name(self) -> str:
        return build_harness_credential_binding_name(
            manifest_id=self.manifest_id,
            agent_name=self.agent_name,
        )

    @property
    def next_run_number(self) -> int:
        return len(self.run_history) + 1

    def snapshot_for_run_number(self, run_number: int | None) -> HarnessRunSnapshot | None:
        if run_number is None:
            return self.last_run
        for snapshot in self.run_history:
            if snapshot.run_number == run_number:
                return snapshot
        return None

    def append_run_snapshot(self, snapshot: HarnessRunSnapshot) -> "HarnessProfile":
        normalized_snapshot = snapshot.with_run_number(self.next_run_number)
        return HarnessProfile(
            manifest_id=self.manifest_id,
            agent_name=self.agent_name,
            runtime_parameters=self.runtime_parameters,
            custom_parameters=self.custom_parameters,
            last_run=normalized_snapshot,
            run_history=self.run_history + (normalized_snapshot,),
        )

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "agent_name": self.agent_name,
            "custom_parameters": dict(self.custom_parameters or {}),
            "manifest_id": self.manifest_id,
            "runtime_parameters": dict(self.runtime_parameters or {}),
        }
        if self.last_run is not None:
            payload["last_run"] = self.last_run.as_dict()
        if self.run_history:
            payload["run_history"] = [snapshot.as_dict() for snapshot in self.run_history]
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "HarnessProfile":
        runtime_parameters = payload.get("runtime_parameters", {})
        custom_parameters = payload.get("custom_parameters", {})
        run_history_payload = payload.get("run_history", [])
        if not isinstance(runtime_parameters, dict):
            raise ValueError("Harness profile 'runtime_parameters' must be a JSON object.")
        if not isinstance(custom_parameters, dict):
            raise ValueError("Harness profile 'custom_parameters' must be a JSON object.")
        if not isinstance(run_history_payload, list):
            raise ValueError("Harness profile 'run_history' must be a JSON array when present.")
        last_run_payload = payload.get("last_run")
        if last_run_payload is not None and not isinstance(last_run_payload, dict):
            raise ValueError("Harness profile 'last_run' must be a JSON object when present.")
        last_run = None
        if last_run_payload is not None:
            last_run = HarnessRunSnapshot.from_dict(last_run_payload)
            if "runtime_parameters" not in last_run_payload:
                last_run = HarnessRunSnapshot(
                    model_factory=last_run.model_factory,
                    sink_specs=last_run.sink_specs,
                    max_cycles=last_run.max_cycles,
                    adapter_arguments=last_run.adapter_arguments,
                    runtime_parameters=dict(runtime_parameters),
                    custom_parameters=last_run.custom_parameters,
                    recorded_at=last_run.recorded_at,
                    run_number=last_run.run_number,
                )
            if "custom_parameters" not in last_run_payload:
                last_run = HarnessRunSnapshot(
                    model_factory=last_run.model_factory,
                    sink_specs=last_run.sink_specs,
                    max_cycles=last_run.max_cycles,
                    adapter_arguments=last_run.adapter_arguments,
                    runtime_parameters=last_run.runtime_parameters,
                    custom_parameters=dict(custom_parameters),
                    recorded_at=last_run.recorded_at,
                    run_number=last_run.run_number,
                )
        return cls(
            manifest_id=str(payload["manifest_id"]),
            agent_name=str(payload["agent_name"]),
            runtime_parameters=dict(runtime_parameters),
            custom_parameters=dict(custom_parameters),
            last_run=last_run,
            run_history=tuple(HarnessRunSnapshot.from_dict(item) for item in run_history_payload),
        )


@dataclass(frozen=True, slots=True)
class HarnessProfileIndexRecord:
    """Persisted locator for one generic harness profile."""

    manifest_id: str
    agent_name: str
    memory_path: Path
    updated_at: str

    def __post_init__(self) -> None:
        normalized_manifest_id = self.manifest_id.strip()
        normalized_agent_name = self.agent_name.strip()
        normalized_updated_at = self.updated_at.strip()
        if not normalized_manifest_id:
            raise ValueError("manifest_id must not be blank.")
        if not normalized_agent_name:
            raise ValueError("agent_name must not be blank.")
        if not normalized_updated_at:
            raise ValueError("updated_at must not be blank.")
        object.__setattr__(self, "manifest_id", normalized_manifest_id)
        object.__setattr__(self, "agent_name", normalized_agent_name)
        object.__setattr__(self, "memory_path", Path(self.memory_path))
        object.__setattr__(self, "updated_at", normalized_updated_at)

    @property
    def key(self) -> tuple[str, str, str]:
        return (
            self.manifest_id,
            self.agent_name,
            self.memory_path.expanduser().resolve().as_posix(),
        )

    def to_dict(self, *, repo_root: Path) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "manifest_id": self.manifest_id,
            "memory_path": serialize_repo_path(self.memory_path, repo_root=repo_root),
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], *, repo_root: Path) -> "HarnessProfileIndexRecord":
        return cls(
            manifest_id=str(payload["manifest_id"]),
            agent_name=str(payload["agent_name"]),
            memory_path=deserialize_repo_path(str(payload["memory_path"]), repo_root=repo_root),
            updated_at=str(payload["updated_at"]),
        )


@dataclass(frozen=True, slots=True)
class HarnessProfileIndex:
    """Persisted collection of known harness profile locations for one repo root."""

    records: tuple[HarnessProfileIndexRecord, ...] = ()

    def __post_init__(self) -> None:
        indexed: dict[tuple[str, str, str], HarnessProfileIndexRecord] = {}
        for record in self.records:
            if not isinstance(record, HarnessProfileIndexRecord):
                raise TypeError("records must contain HarnessProfileIndexRecord instances.")
            indexed[record.key] = record
        ordered = tuple(
            indexed[key]
            for key in sorted(
                indexed,
                key=lambda item: (
                    indexed[item].agent_name,
                    indexed[item].manifest_id,
                    indexed[item].memory_path.as_posix(),
                ),
            )
        )
        object.__setattr__(self, "records", ordered)

    def list(
        self,
        *,
        agent_name: str | None = None,
        manifest_id: str | None = None,
    ) -> tuple[HarnessProfileIndexRecord, ...]:
        filtered = self.records
        if agent_name is not None:
            normalized_agent_name = agent_name.strip()
            filtered = tuple(record for record in filtered if record.agent_name == normalized_agent_name)
        if manifest_id is not None:
            normalized_manifest_id = manifest_id.strip()
            filtered = tuple(record for record in filtered if record.manifest_id == normalized_manifest_id)
        return filtered

    def upsert(self, record: HarnessProfileIndexRecord) -> "HarnessProfileIndex":
        indexed = {item.key: item for item in self.records}
        indexed[record.key] = record
        return HarnessProfileIndex(records=tuple(indexed.values()))

    def to_dict(self, *, repo_root: Path) -> dict[str, Any]:
        return {"records": [record.to_dict(repo_root=repo_root) for record in self.records]}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], *, repo_root: Path) -> "HarnessProfileIndex":
        raw_records = payload.get("records", [])
        if not isinstance(raw_records, list):
            raise ValueError("Harness profile index payload must define 'records' as a list.")
        return cls(
            records=tuple(
                HarnessProfileIndexRecord.from_dict(item, repo_root=repo_root)
                for item in raw_records
            )
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
        last_run: HarnessRunSnapshot | None | object = _UNSET,
        run_history: tuple[HarnessRunSnapshot, ...] | object = _UNSET,
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
            last_run=(current.last_run if last_run is _UNSET else last_run),
            run_history=(current.run_history if run_history is _UNSET else run_history),
        )
        self.save(next_profile)
        return next_profile


def _normalize_run_history(
    *,
    run_history: tuple[HarnessRunSnapshot, ...],
    last_run: HarnessRunSnapshot | None,
) -> tuple[HarnessRunSnapshot, ...]:
    snapshots = list(run_history)
    if not snapshots and last_run is not None:
        snapshots.append(last_run)
    elif snapshots and last_run is not None and not _run_snapshots_match(snapshots[-1], last_run):
        snapshots.append(last_run)

    normalized: list[HarnessRunSnapshot] = []
    for index, snapshot in enumerate(snapshots, start=1):
        if not isinstance(snapshot, HarnessRunSnapshot):
            raise TypeError("run_history must contain HarnessRunSnapshot instances.")
        normalized.append(snapshot.with_run_number(index))
    return tuple(normalized)


def _run_snapshots_match(left: HarnessRunSnapshot, right: HarnessRunSnapshot) -> bool:
    return (
        left.model_factory == right.model_factory
        and left.model_spec == right.model_spec
        and left.model_profile == right.model_profile
        and left.sink_specs == right.sink_specs
        and left.max_cycles == right.max_cycles
        and left.adapter_arguments == right.adapter_arguments
        and left.runtime_parameters == right.runtime_parameters
        and left.custom_parameters == right.custom_parameters
        and left.recorded_at == right.recorded_at
    )


@dataclass(slots=True)
class HarnessProfileIndexStore:
    """Load and save the repo-scoped generic harness-profile discovery index."""

    repo_root: Path | str = "."

    def __post_init__(self) -> None:
        self.repo_root = Path(self.repo_root).expanduser().resolve()

    @property
    def memory_root(self) -> Path:
        return self.repo_root / DEFAULT_MEMORY_ROOT_DIRNAME

    @property
    def index_path(self) -> Path:
        return self.memory_root / DEFAULT_HARNESS_PROFILE_INDEX_FILENAME

    def load(self) -> HarnessProfileIndex:
        if not self.index_path.exists():
            return HarnessProfileIndex()
        raw = self.index_path.read_text(encoding="utf-8").strip()
        if not raw:
            return HarnessProfileIndex()
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("Harness profile index file must contain a JSON object.")
        return HarnessProfileIndex.from_dict(payload, repo_root=self.repo_root)

    def save(self, index: HarnessProfileIndex) -> Path:
        self.memory_root.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(
            json.dumps(index.to_dict(repo_root=self.repo_root), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return self.index_path

    def list(
        self,
        *,
        agent_name: str | None = None,
        manifest_id: str | None = None,
    ) -> tuple[HarnessProfileIndexRecord, ...]:
        return self.load().list(agent_name=agent_name, manifest_id=manifest_id)

    def upsert(
        self,
        *,
        manifest_id: str,
        agent_name: str,
        memory_path: str | Path,
        updated_at: str | None = None,
    ) -> HarnessProfileIndexRecord:
        record = HarnessProfileIndexRecord(
            manifest_id=manifest_id,
            agent_name=agent_name,
            memory_path=Path(memory_path),
            updated_at=updated_at or _utcnow(),
        )
        index = self.load()
        self.save(index.upsert(record))
        return record


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


__all__ = [
    "DEFAULT_HARNESS_PROFILE_FILENAME",
    "DEFAULT_HARNESS_PROFILE_INDEX_FILENAME",
    "HarnessProfile",
    "HarnessProfileIndex",
    "HarnessProfileIndexRecord",
    "HarnessProfileIndexStore",
    "HarnessProfileStore",
    "HarnessRunSnapshot",
    "build_harness_credential_binding_name",
]
