"""Shared DTO base protocols and coercion helpers."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SerializableDTO(Protocol):
    """Protocol implemented by shared DTOs that serialize into JSON-safe mappings."""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe mapping representation of the DTO."""


def coerce_serializable_mapping(
    payload: SerializableDTO | Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Return a detached mapping for DTO or mapping inputs."""
    if payload is None:
        return {}
    if isinstance(payload, SerializableDTO):
        return deepcopy(payload.to_dict())
    if isinstance(payload, Mapping):
        return {str(key): deepcopy(value) for key, value in payload.items()}
    raise TypeError("DTO payload must be a mapping or SerializableDTO when provided.")


__all__ = ["SerializableDTO", "coerce_serializable_mapping"]
