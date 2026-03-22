"""Core ledger data structures and low-level serialization helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Mapping, Protocol
from uuid import uuid4

DEFAULT_HARNESSIQ_DIRNAME = ".harnessiq"
DEFAULT_LEDGER_FILENAME = "runs.jsonl"
DEFAULT_CONNECTIONS_FILENAME = "connections.json"

LedgerStatus = Literal["completed", "paused", "max_cycles_reached", "error"]


@dataclass(frozen=True, slots=True)
class LedgerEntry:
    """Universal audit record emitted after agent runs finish."""

    run_id: str
    agent_name: str
    started_at: datetime
    finished_at: datetime
    status: LedgerStatus
    reset_count: int
    outputs: dict[str, Any]
    tags: list[str]
    metadata: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "finished_at": _isoformat_z(self.finished_at),
            "metadata": _json_safe(self.metadata),
            "outputs": _json_safe(self.outputs),
            "reset_count": self.reset_count,
            "run_id": self.run_id,
            "started_at": _isoformat_z(self.started_at),
            "status": self.status,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LedgerEntry":
        return cls(
            run_id=str(payload["run_id"]),
            agent_name=str(payload["agent_name"]),
            started_at=_parse_datetime(str(payload["started_at"])),
            finished_at=_parse_datetime(str(payload["finished_at"])),
            status=str(payload["status"]),  # type: ignore[arg-type]
            reset_count=int(payload.get("reset_count", 0)),
            outputs=dict(payload.get("outputs", {})),
            tags=[str(tag) for tag in payload.get("tags", [])],
            metadata=dict(payload.get("metadata", {})),
        )


class OutputSink(Protocol):
    """Write-only post-run sink contract."""

    def on_run_complete(self, entry: LedgerEntry) -> None:
        """Persist or export a completed ledger entry."""


def new_run_id() -> str:
    return str(uuid4())


def parse_relative_duration(spec: str) -> timedelta:
    normalized = spec.strip().lower()
    if not normalized:
        raise ValueError("Relative duration must not be blank.")
    unit = normalized[-1]
    value_text = normalized[:-1]
    if unit not in {"m", "h", "d"} or not value_text:
        raise ValueError("Relative durations must use the form <number><m|h|d>, for example 30m, 6h, or 7d.")
    value = int(value_text)
    if unit == "m":
        return timedelta(minutes=value)
    if unit == "h":
        return timedelta(hours=value)
    return timedelta(days=value)


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return _isoformat_z(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    as_dict = getattr(value, "as_dict", None)
    if callable(as_dict):
        return _json_safe(as_dict())
    return str(value)


def _parse_datetime(text: str) -> datetime:
    normalized = text.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    return datetime.fromisoformat(normalized).astimezone(timezone.utc)


def _isoformat_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _format_duration(duration: timedelta) -> str:
    total_seconds = max(0, int(duration.total_seconds()))
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def _safe_slug(value: str) -> str:
    cleaned = "".join(character if character.isalnum() or character in {"-", "_"} else "-" for character in value)
    collapsed = "-".join(part for part in cleaned.split("-") if part)
    return collapsed or "agent"


def _truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 3)] + "..."


__all__ = [
    "DEFAULT_CONNECTIONS_FILENAME",
    "DEFAULT_HARNESSIQ_DIRNAME",
    "DEFAULT_LEDGER_FILENAME",
    "LedgerEntry",
    "LedgerStatus",
    "OutputSink",
    "new_run_id",
    "parse_relative_duration",
]
