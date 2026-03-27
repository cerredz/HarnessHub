"""Filesystem-backed registry for SDK-level agent instances."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from harnessiq.shared.dtos import AgentInstancePayload
from harnessiq.utils.agent_ids import (
    build_agent_instance_dirname,
    build_agent_instance_id,
    build_default_instance_name,
    fingerprint_agent_payload,
    normalize_agent_name,
)
from harnessiq.utils.path_serialization import deserialize_repo_path, serialize_repo_path

DEFAULT_AGENT_INSTANCE_REGISTRY_FILENAME = "agent_instances.json"
DEFAULT_AGENT_INSTANCE_MEMORY_DIRNAME = "agents"
DEFAULT_MEMORY_ROOT_DIRNAME = "memory"


@dataclass(frozen=True, slots=True)
class AgentInstanceRecord:
    """Persisted metadata for one logical agent instance."""

    agent_name: str
    instance_id: str
    instance_name: str
    payload_fingerprint: str
    payload: AgentInstancePayload
    memory_path: Path
    created_at: str
    updated_at: str

    def __post_init__(self) -> None:
        normalized_agent_name = normalize_agent_name(self.agent_name)
        if not self.instance_id.strip():
            raise ValueError("instance_id must not be blank.")
        if not self.instance_name.strip():
            raise ValueError("instance_name must not be blank.")
        object.__setattr__(self, "agent_name", normalized_agent_name)
        object.__setattr__(self, "instance_id", self.instance_id.strip())
        object.__setattr__(self, "instance_name", self.instance_name.strip())
        object.__setattr__(self, "payload", AgentInstancePayload.from_dict(self.payload))
        object.__setattr__(self, "memory_path", Path(self.memory_path))

    def to_dict(self, *, repo_root: Path) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "created_at": self.created_at,
            "instance_id": self.instance_id,
            "instance_name": self.instance_name,
            "memory_path": serialize_repo_path(self.memory_path, repo_root=repo_root),
            "payload": self.payload.to_dict(),
            "payload_fingerprint": self.payload_fingerprint,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], *, repo_root: Path) -> "AgentInstanceRecord":
        return cls(
            agent_name=str(payload["agent_name"]),
            instance_id=str(payload["instance_id"]),
            instance_name=str(payload["instance_name"]),
            payload_fingerprint=str(payload["payload_fingerprint"]),
            payload=AgentInstancePayload.from_dict(payload.get("payload", {})),
            memory_path=deserialize_repo_path(str(payload["memory_path"]), repo_root=repo_root),
            created_at=str(payload["created_at"]),
            updated_at=str(payload["updated_at"]),
        )

    def with_updates(
        self,
        *,
        instance_name: str | None = None,
        memory_path: str | Path | None = None,
        updated_at: str | None = None,
    ) -> "AgentInstanceRecord":
        return AgentInstanceRecord(
            agent_name=self.agent_name,
            instance_id=self.instance_id,
            instance_name=instance_name or self.instance_name,
            payload_fingerprint=self.payload_fingerprint,
            payload=self.payload,
            memory_path=Path(memory_path) if memory_path is not None else self.memory_path,
            created_at=self.created_at,
            updated_at=updated_at or self.updated_at,
        )


@dataclass(frozen=True, slots=True)
class AgentInstanceCatalog:
    """Persisted collection of agent instances."""

    records: tuple[AgentInstanceRecord, ...] = ()

    def __post_init__(self) -> None:
        indexed: dict[str, AgentInstanceRecord] = {}
        for record in self.records:
            if not isinstance(record, AgentInstanceRecord):
                raise TypeError("records must contain AgentInstanceRecord instances.")
            indexed[record.instance_id] = record
        ordered = tuple(indexed[key] for key in sorted(indexed))
        object.__setattr__(self, "records", ordered)

    def get(self, instance_id: str) -> AgentInstanceRecord:
        normalized = instance_id.strip()
        for record in self.records:
            if record.instance_id == normalized:
                return record
        raise KeyError(f"No agent instance exists with id '{instance_id}'.")

    def maybe_get(self, instance_id: str) -> AgentInstanceRecord | None:
        normalized = instance_id.strip()
        for record in self.records:
            if record.instance_id == normalized:
                return record
        return None

    def list(self, *, agent_name: str | None = None) -> tuple[AgentInstanceRecord, ...]:
        if agent_name is None:
            return self.records
        normalized_agent_name = normalize_agent_name(agent_name)
        return tuple(record for record in self.records if record.agent_name == normalized_agent_name)

    def upsert(self, record: AgentInstanceRecord) -> "AgentInstanceCatalog":
        indexed = {item.instance_id: item for item in self.records}
        indexed[record.instance_id] = record
        return AgentInstanceCatalog(records=tuple(indexed.values()))

    def to_dict(self, *, repo_root: Path) -> dict[str, Any]:
        return {"records": [record.to_dict(repo_root=repo_root) for record in self.records]}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], *, repo_root: Path) -> "AgentInstanceCatalog":
        raw_records = payload.get("records", [])
        if not isinstance(raw_records, list):
            raise ValueError("Agent instance catalog payload must define 'records' as a list.")
        return cls(records=tuple(AgentInstanceRecord.from_dict(item, repo_root=repo_root) for item in raw_records))


@dataclass(slots=True)
class AgentInstanceStore:
    """Load, save, list, and resolve agent instances for one repo/workspace root."""

    repo_root: Path | str = "."

    def __post_init__(self) -> None:
        self.repo_root = Path(self.repo_root).expanduser().resolve()

    @property
    def memory_root(self) -> Path:
        return self.repo_root / DEFAULT_MEMORY_ROOT_DIRNAME

    @property
    def registry_path(self) -> Path:
        return self.memory_root / DEFAULT_AGENT_INSTANCE_REGISTRY_FILENAME

    @property
    def default_instances_root(self) -> Path:
        return self.memory_root / DEFAULT_AGENT_INSTANCE_MEMORY_DIRNAME

    def load(self) -> AgentInstanceCatalog:
        if not self.registry_path.exists():
            return AgentInstanceCatalog()
        raw = self.registry_path.read_text(encoding="utf-8").strip()
        if not raw:
            return AgentInstanceCatalog()
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("Agent instance registry must contain a JSON object.")
        return AgentInstanceCatalog.from_dict(payload, repo_root=self.repo_root)

    def save(self, catalog: AgentInstanceCatalog) -> Path:
        self.memory_root.mkdir(parents=True, exist_ok=True)
        self.registry_path.write_text(
            json.dumps(catalog.to_dict(repo_root=self.repo_root), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return self.registry_path

    def list_instances(self, *, agent_name: str | None = None) -> tuple[AgentInstanceRecord, ...]:
        return self.load().list(agent_name=agent_name)

    def get(self, instance_id: str) -> AgentInstanceRecord:
        return self.load().get(instance_id)

    def resolve(
        self,
        *,
        agent_name: str,
        payload: AgentInstancePayload | Mapping[str, Any] | None,
        instance_name: str | None = None,
        memory_path: str | Path | None = None,
    ) -> AgentInstanceRecord:
        normalized_agent_name = normalize_agent_name(agent_name)
        normalized_payload = AgentInstancePayload.from_dict(payload)
        fingerprint = fingerprint_agent_payload(normalized_payload.to_dict())
        instance_id = build_agent_instance_id(
            normalized_agent_name,
            normalized_payload.to_dict(),
        )
        catalog = self.load()
        existing = catalog.maybe_get(instance_id)
        timestamp = _utcnow()
        resolved_memory_path = self._resolve_memory_path(
            agent_name=normalized_agent_name,
            instance_id=instance_id,
            memory_path=memory_path,
        )

        if existing is not None:
            migrated_memory_path: Path | None = None
            if (
                memory_path is None
                and existing.memory_path == self._legacy_default_memory_path(agent_name=normalized_agent_name, instance_id=instance_id)
                and existing.memory_path != resolved_memory_path
            ):
                migrated_memory_path = resolved_memory_path
            updated = existing.with_updates(
                instance_name=instance_name.strip() if instance_name and instance_name.strip() else None,
                memory_path=migrated_memory_path,
                updated_at=timestamp,
            )
            self.save(catalog.upsert(updated))
            return updated

        resolved_instance_name = instance_name.strip() if instance_name and instance_name.strip() else build_default_instance_name(
            normalized_agent_name,
            normalized_payload,
            memory_path=resolved_memory_path,
        )
        record = AgentInstanceRecord(
            agent_name=normalized_agent_name,
            instance_id=instance_id,
            instance_name=resolved_instance_name,
            payload_fingerprint=fingerprint,
            payload=normalized_payload,
            memory_path=resolved_memory_path,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.save(catalog.upsert(record))
        return record

    def get_for_payload(
        self,
        *,
        agent_name: str,
        payload: AgentInstancePayload | Mapping[str, Any] | None,
    ) -> AgentInstanceRecord:
        normalized_payload = AgentInstancePayload.from_dict(payload)
        instance_id = build_agent_instance_id(agent_name, normalized_payload.to_dict())
        return self.get(instance_id)

    def _resolve_memory_path(
        self,
        *,
        agent_name: str,
        instance_id: str,
        memory_path: str | Path | None,
    ) -> Path:
        if memory_path is None:
            return self.default_instances_root / normalize_agent_name(agent_name) / build_agent_instance_dirname(instance_id)
        candidate = Path(memory_path).expanduser()
        if not candidate.is_absolute():
            return self.repo_root / candidate
        return candidate

    def _legacy_default_memory_path(
        self,
        *,
        agent_name: str,
        instance_id: str,
    ) -> Path:
        return self.default_instances_root / normalize_agent_name(agent_name) / instance_id


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = [
    "AgentInstanceCatalog",
    "AgentInstanceRecord",
    "AgentInstanceStore",
    "DEFAULT_AGENT_INSTANCE_MEMORY_DIRNAME",
    "DEFAULT_AGENT_INSTANCE_REGISTRY_FILENAME",
    "DEFAULT_MEMORY_ROOT_DIRNAME",
]
