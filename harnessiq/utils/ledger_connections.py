"""Connection persistence and sink-spec parsing helpers for the ledger subsystem."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from harnessiq.utils.ledger_models import (
    DEFAULT_CONNECTIONS_FILENAME,
    DEFAULT_HARNESSIQ_DIRNAME,
    DEFAULT_LEDGER_FILENAME,
    _json_safe,
)


@dataclass(frozen=True, slots=True)
class SinkConnection:
    """Persisted global sink connection entry."""

    name: str
    sink_type: str
    config: dict[str, Any]
    enabled: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "config", dict(self.config))
        object.__setattr__(self, "name", self.name.strip())
        object.__setattr__(self, "sink_type", self.sink_type.strip())
        if not self.name:
            raise ValueError("Connection name must not be blank.")
        if not self.sink_type:
            raise ValueError("Connection sink_type must not be blank.")

    def as_dict(self) -> dict[str, Any]:
        return {
            "config": _json_safe(self.config),
            "enabled": self.enabled,
            "name": self.name,
            "sink_type": self.sink_type,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SinkConnection":
        return cls(
            name=str(payload["name"]),
            sink_type=str(payload["sink_type"]),
            config=dict(payload.get("config", {})),
            enabled=bool(payload.get("enabled", True)),
        )


@dataclass(frozen=True, slots=True)
class ConnectionsConfig:
    """Collection of persisted sink connections."""

    connections: tuple[SinkConnection, ...] = ()

    def __post_init__(self) -> None:
        normalized = tuple(self.connections)
        unique_names: set[str] = set()
        for connection in normalized:
            if connection.name in unique_names:
                raise ValueError(f"Duplicate sink connection '{connection.name}'.")
            unique_names.add(connection.name)
        object.__setattr__(self, "connections", normalized)

    def as_dict(self) -> dict[str, Any]:
        return {"connections": [connection.as_dict() for connection in self.connections]}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ConnectionsConfig":
        raw_connections = payload.get("connections", [])
        if not isinstance(raw_connections, list):
            raise ValueError("Connections config must define 'connections' as a list.")
        return cls(connections=tuple(SinkConnection.from_dict(item) for item in raw_connections))

    def upsert(self, connection: SinkConnection) -> "ConnectionsConfig":
        indexed = {item.name: item for item in self.connections}
        indexed[connection.name] = connection
        return ConnectionsConfig(connections=tuple(indexed[name] for name in sorted(indexed)))

    def remove(self, name: str) -> "ConnectionsConfig":
        normalized = name.strip()
        indexed = {item.name: item for item in self.connections}
        indexed.pop(normalized, None)
        return ConnectionsConfig(connections=tuple(indexed[key] for key in sorted(indexed)))

    def enabled_connections(self) -> tuple[SinkConnection, ...]:
        return tuple(connection for connection in self.connections if connection.enabled)


@dataclass(slots=True)
class ConnectionsConfigStore:
    """Persist global sink connections under the HarnessIQ home directory."""

    home_dir: Path | str | None = None

    def __post_init__(self) -> None:
        self.home_dir = harnessiq_home_dir(self.home_dir)

    @property
    def config_path(self) -> Path:
        return Path(self.home_dir) / DEFAULT_CONNECTIONS_FILENAME

    def load(self) -> ConnectionsConfig:
        path = self.config_path
        if not path.exists():
            return ConnectionsConfig()
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return ConnectionsConfig()
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("Connections config file must contain a JSON object.")
        return ConnectionsConfig.from_dict(payload)

    def save(self, config: ConnectionsConfig) -> Path:
        path = self.config_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(config.as_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return path

    def upsert(self, connection: SinkConnection) -> Path:
        return self.save(self.load().upsert(connection))

    def remove(self, name: str) -> Path:
        return self.save(self.load().remove(name))


def harnessiq_home_dir(home_dir: Path | str | None = None) -> Path:
    if home_dir is not None:
        return Path(home_dir).expanduser().resolve()
    override = os.environ.get("HARNESSIQ_HOME", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    try:
        preferred = (Path.home() / DEFAULT_HARNESSIQ_DIRNAME).expanduser().resolve()
    except RuntimeError:
        preferred = None
    if preferred is not None:
        try:
            preferred.mkdir(parents=True, exist_ok=True)
            return preferred
        except OSError:
            pass
    fallback = (Path.cwd() / DEFAULT_HARNESSIQ_DIRNAME).resolve()
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def default_ledger_path(home_dir: Path | str | None = None) -> Path:
    return harnessiq_home_dir(home_dir) / DEFAULT_LEDGER_FILENAME


def parse_sink_spec(spec: str) -> tuple[str, dict[str, Any]]:
    normalized = spec.strip()
    if not normalized:
        raise ValueError("Sink spec must not be blank.")
    sink_type, separator, remainder = normalized.partition(":")
    if not separator:
        raise ValueError(
            "Sink specs must use the form kind:value or kind:key=value,key=value."
        )
    sink_type = sink_type.strip().lower()
    remainder = remainder.strip()
    if not remainder:
        return sink_type, {}
    if "=" not in remainder:
        if sink_type == "jsonl":
            return sink_type, {"path": remainder}
        if sink_type == "obsidian":
            return sink_type, {"vault_path": remainder}
        if sink_type in {"slack", "discord"}:
            return sink_type, {"webhook_url": remainder}
        return sink_type, {"value": remainder}
    config: dict[str, Any] = {}
    for part in remainder.split(","):
        key, item_separator, value = part.partition("=")
        if not item_separator:
            raise ValueError(f"Invalid sink assignment '{part}' in spec '{spec}'.")
        config[key.strip()] = _parse_scalar(value.strip())
    return sink_type, config


def _parse_scalar(value: str) -> Any:
    if not value:
        return ""
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


__all__ = [
    "ConnectionsConfig",
    "ConnectionsConfigStore",
    "SinkConnection",
    "default_ledger_path",
    "harnessiq_home_dir",
    "parse_sink_spec",
]
