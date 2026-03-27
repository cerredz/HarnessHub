"""Shared DTOs for agent-layer boundaries."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json

from harnessiq.shared.dtos.base import SerializableDTO, coerce_serializable_mapping


@dataclass(frozen=True, slots=True)
class AgentInstancePayload(Mapping[str, Any]):
    """Typed envelope for persisted agent instance payload data."""

    entries: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "entries", _normalize_payload(self.entries))

    def __getitem__(self, key: str) -> Any:
        return self.entries[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.entries)

    def __len__(self) -> int:
        return len(self.entries)

    def to_dict(self) -> dict[str, Any]:
        """Return a detached JSON-safe mapping."""
        return dict(self.entries)

    @classmethod
    def from_dict(
        cls,
        payload: SerializableDTO | Mapping[str, Any] | None,
    ) -> "AgentInstancePayload":
        """Build a payload envelope from a DTO, mapping, or null input."""
        return cls(entries=coerce_serializable_mapping(payload))


def _normalize_payload(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    if payload is None:
        return {}
    return {
        str(key): _normalize_value(value)
        for key, value in sorted(payload.items(), key=lambda item: str(item[0]))
    }


def _normalize_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, Mapping):
        return {
            str(key): _normalize_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_normalize_value(item) for item in value]
    if isinstance(value, set):
        normalized_items = [_normalize_value(item) for item in value]
        return sorted(
            normalized_items,
            key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=True),
        )
    return str(value)


__all__ = ["AgentInstancePayload"]
