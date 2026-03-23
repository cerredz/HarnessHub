"""Stable helpers for agent instance payloads and identifiers."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping


def normalize_agent_name(agent_name: str) -> str:
    """Return a filesystem-safe agent identifier."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", agent_name.strip()).strip("-")
    if not cleaned:
        raise ValueError("agent_name must contain at least one alphanumeric character.")
    return cleaned


def normalize_agent_payload(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a stable, JSON-serializable payload snapshot."""
    if payload is None:
        return {}
    if not isinstance(payload, Mapping):
        raise TypeError("payload must be a mapping when provided.")
    return {str(key): _normalize_value(value) for key, value in sorted(payload.items(), key=lambda item: str(item[0]))}


def fingerprint_agent_payload(payload: Mapping[str, Any] | None) -> str:
    """Return a stable SHA-256 fingerprint for an agent payload."""
    normalized = normalize_agent_payload(payload)
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_agent_instance_id(agent_name: str, payload: Mapping[str, Any] | None) -> str:
    """Return the deterministic instance id for ``agent_name`` + ``payload``."""
    normalized_name = normalize_agent_name(agent_name)
    fingerprint = fingerprint_agent_payload(payload)
    return f"{normalized_name}::{fingerprint[:16]}"


def build_agent_instance_dirname(instance_id: str) -> str:
    """Return a filesystem-safe directory name for a stable ``instance_id``."""
    normalized = instance_id.strip()
    if not normalized:
        raise ValueError("instance_id must not be blank.")
    collapsed = normalized.replace("::", "__")
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", collapsed).strip("-")
    if not cleaned:
        raise ValueError("instance_id must contain at least one filesystem-safe character.")
    return cleaned


def build_default_instance_name(
    agent_name: str,
    payload: Mapping[str, Any] | None,
    *,
    memory_path: str | Path | None = None,
) -> str:
    """Return a human-readable default instance name."""
    if memory_path is not None:
        candidate = Path(memory_path)
        if candidate.name:
            return candidate.name
    normalized_name = normalize_agent_name(agent_name)
    return f"{normalized_name}-{fingerprint_agent_payload(payload)[:8]}"


def _normalize_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, Mapping):
        return {str(key): _normalize_value(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (list, tuple)):
        return [_normalize_value(item) for item in value]
    if isinstance(value, set):
        normalized_items = [_normalize_value(item) for item in value]
        return sorted(normalized_items, key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=True))
    return str(value)


__all__ = [
    "build_agent_instance_dirname",
    "build_agent_instance_id",
    "build_default_instance_name",
    "fingerprint_agent_payload",
    "normalize_agent_name",
    "normalize_agent_payload",
]
