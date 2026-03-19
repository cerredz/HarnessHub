"""Shared models, memory store, and pluggable storage backend for the leads agent."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, Sequence, runtime_checkable
from urllib.parse import urlsplit, urlunsplit

from harnessiq.utils.run_storage import FileSystemStorageBackend

ICPS_DIRNAME = "icps"
LEADS_STORAGE_DIRNAME = "lead_storage"
RUN_CONFIG_FILENAME = "run_config.json"
RUN_STATE_FILENAME = "run_state.json"
SAVED_LEADS_FILENAME = "saved_leads.json"

_ICP_STATUS_VALUES = frozenset({"pending", "active", "completed"})
_RUN_STATUS_VALUES = frozenset({"pending", "running", "completed"})


@dataclass(frozen=True, slots=True)
class LeadICP:
    """One ideal customer profile definition for the leads agent."""

    label: str
    description: str = ""
    key: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("LeadICP label must not be blank.")
        resolved_key = self.key.strip() or _slugify(self.label)
        if not resolved_key:
            raise ValueError("LeadICP key must not be blank.")
        object.__setattr__(self, "key", resolved_key)

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "description": self.description,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LeadICP":
        return cls(
            key=str(data.get("key", "")),
            label=str(data["label"]),
            description=str(data.get("description", "")),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class LeadRunConfig:
    """Durable run configuration for a multi-ICP leads discovery run."""

    company_background: str
    icps: tuple[LeadICP, ...]
    platforms: tuple[str, ...]
    search_summary_every: int = 500
    search_tail_size: int = 20
    max_leads_per_icp: int | None = None

    def __post_init__(self) -> None:
        if not self.company_background.strip():
            raise ValueError("LeadRunConfig company_background must not be blank.")
        if not self.icps:
            raise ValueError("LeadRunConfig icps must not be empty.")
        if not self.platforms:
            raise ValueError("LeadRunConfig platforms must not be empty.")
        if self.search_summary_every <= 0:
            raise ValueError("LeadRunConfig search_summary_every must be greater than zero.")
        if self.search_tail_size < 0:
            raise ValueError("LeadRunConfig search_tail_size must be zero or greater.")
        if self.max_leads_per_icp is not None and self.max_leads_per_icp <= 0:
            raise ValueError("LeadRunConfig max_leads_per_icp must be greater than zero when set.")

    def as_dict(self) -> dict[str, Any]:
        return {
            "company_background": self.company_background,
            "icps": [icp.as_dict() for icp in self.icps],
            "platforms": list(self.platforms),
            "search_summary_every": self.search_summary_every,
            "search_tail_size": self.search_tail_size,
            "max_leads_per_icp": self.max_leads_per_icp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LeadRunConfig":
        return cls(
            company_background=str(data["company_background"]),
            icps=tuple(LeadICP.from_dict(item) for item in data.get("icps", [])),
            platforms=tuple(str(item) for item in data.get("platforms", [])),
            search_summary_every=int(data.get("search_summary_every", 500)),
            search_tail_size=int(data.get("search_tail_size", 20)),
            max_leads_per_icp=int(data["max_leads_per_icp"]) if data.get("max_leads_per_icp") is not None else None,
        )


@dataclass(frozen=True, slots=True)
class LeadRunState:
    """Progress tracking for one rotating multi-ICP leads run."""

    run_id: str
    active_icp_index: int = 0
    status: str = "pending"
    started_at: str | None = None
    completed_at: str | None = None

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise ValueError("LeadRunState run_id must not be blank.")
        if self.active_icp_index < 0:
            raise ValueError("LeadRunState active_icp_index must be zero or greater.")
        if self.status not in _RUN_STATUS_VALUES:
            allowed = ", ".join(sorted(_RUN_STATUS_VALUES))
            raise ValueError(f"LeadRunState status must be one of: {allowed}.")

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "active_icp_index": self.active_icp_index,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LeadRunState":
        return cls(
            run_id=str(data["run_id"]),
            active_icp_index=int(data.get("active_icp_index", 0)),
            status=str(data.get("status", "pending")),
            started_at=str(data["started_at"]) if data.get("started_at") else None,
            completed_at=str(data["completed_at"]) if data.get("completed_at") else None,
        )


@dataclass(frozen=True, slots=True)
class LeadSearchRecord:
    """One deterministic search attempt recorded for an ICP."""

    sequence: int
    icp_key: str
    platform: str
    query: str
    recorded_at: str
    filters: dict[str, Any] = field(default_factory=dict)
    result_count: int | None = None
    outcome: str = ""
    new_leads: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.sequence <= 0:
            raise ValueError("LeadSearchRecord sequence must be greater than zero.")
        if not self.icp_key.strip():
            raise ValueError("LeadSearchRecord icp_key must not be blank.")
        if not self.platform.strip():
            raise ValueError("LeadSearchRecord platform must not be blank.")
        if not self.query.strip():
            raise ValueError("LeadSearchRecord query must not be blank.")
        if self.result_count is not None and self.result_count < 0:
            raise ValueError("LeadSearchRecord result_count must be zero or greater when set.")
        if self.new_leads < 0:
            raise ValueError("LeadSearchRecord new_leads must be zero or greater.")

    def as_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "icp_key": self.icp_key,
            "platform": self.platform,
            "query": self.query,
            "recorded_at": self.recorded_at,
            "filters": dict(self.filters),
            "result_count": self.result_count,
            "outcome": self.outcome,
            "new_leads": self.new_leads,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LeadSearchRecord":
        return cls(
            sequence=int(data["sequence"]),
            icp_key=str(data["icp_key"]),
            platform=str(data["platform"]),
            query=str(data["query"]),
            recorded_at=str(data["recorded_at"]),
            filters=dict(data.get("filters", {})),
            result_count=int(data["result_count"]) if data.get("result_count") is not None else None,
            outcome=str(data.get("outcome", "")),
            new_leads=int(data.get("new_leads", 0)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class LeadSearchSummary:
    """A summary that replaces an older block of search entries for one ICP."""

    summary_id: str
    icp_key: str
    created_at: str
    content: str
    replaced_search_count: int
    last_sequence: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.summary_id.strip():
            raise ValueError("LeadSearchSummary summary_id must not be blank.")
        if not self.icp_key.strip():
            raise ValueError("LeadSearchSummary icp_key must not be blank.")
        if not self.content.strip():
            raise ValueError("LeadSearchSummary content must not be blank.")
        if self.replaced_search_count <= 0:
            raise ValueError("LeadSearchSummary replaced_search_count must be greater than zero.")
        if self.last_sequence is not None and self.last_sequence <= 0:
            raise ValueError("LeadSearchSummary last_sequence must be greater than zero when set.")

    def as_dict(self) -> dict[str, Any]:
        return {
            "summary_id": self.summary_id,
            "icp_key": self.icp_key,
            "created_at": self.created_at,
            "content": self.content,
            "replaced_search_count": self.replaced_search_count,
            "last_sequence": self.last_sequence,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LeadSearchSummary":
        return cls(
            summary_id=str(data["summary_id"]),
            icp_key=str(data["icp_key"]),
            created_at=str(data["created_at"]),
            content=str(data["content"]),
            replaced_search_count=int(data["replaced_search_count"]),
            last_sequence=int(data["last_sequence"]) if data.get("last_sequence") is not None else None,
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class LeadRecord:
    """A saved prospect discovered while searching for one ICP."""

    full_name: str
    company_name: str
    title: str
    icp_key: str
    provider: str
    found_at: str
    email: str | None = None
    linkedin_url: str | None = None
    phone: str | None = None
    location: str | None = None
    provider_person_id: str | None = None
    source_search_sequence: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.full_name.strip():
            raise ValueError("LeadRecord full_name must not be blank.")
        if not self.icp_key.strip():
            raise ValueError("LeadRecord icp_key must not be blank.")
        if not self.provider.strip():
            raise ValueError("LeadRecord provider must not be blank.")
        if self.source_search_sequence is not None and self.source_search_sequence <= 0:
            raise ValueError("LeadRecord source_search_sequence must be greater than zero when set.")

    def dedupe_key(self) -> str:
        if self.provider_person_id:
            provider = _normalize_text(self.provider)
            person_id = _normalize_text(self.provider_person_id)
            return f"provider:{provider}:{person_id}"
        if self.linkedin_url:
            return f"linkedin:{_normalize_url(self.linkedin_url)}"
        if self.email:
            return f"email:{_normalize_text(self.email)}"
        name = _normalize_text(self.full_name)
        company = _normalize_text(self.company_name)
        title = _normalize_text(self.title)
        if name and company:
            return f"name_company:{name}:{company}"
        if name and title:
            return f"name_title:{name}:{title}"
        return f"name:{name}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "full_name": self.full_name,
            "company_name": self.company_name,
            "title": self.title,
            "icp_key": self.icp_key,
            "provider": self.provider,
            "found_at": self.found_at,
            "email": self.email,
            "linkedin_url": self.linkedin_url,
            "phone": self.phone,
            "location": self.location,
            "provider_person_id": self.provider_person_id,
            "source_search_sequence": self.source_search_sequence,
            "metadata": dict(self.metadata),
            "dedupe_key": self.dedupe_key(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LeadRecord":
        return cls(
            full_name=str(data["full_name"]),
            company_name=str(data.get("company_name", "")),
            title=str(data.get("title", "")),
            icp_key=str(data["icp_key"]),
            provider=str(data["provider"]),
            found_at=str(data["found_at"]),
            email=str(data["email"]) if data.get("email") else None,
            linkedin_url=str(data["linkedin_url"]) if data.get("linkedin_url") else None,
            phone=str(data["phone"]) if data.get("phone") else None,
            location=str(data["location"]) if data.get("location") else None,
            provider_person_id=str(data["provider_person_id"]) if data.get("provider_person_id") else None,
            source_search_sequence=int(data["source_search_sequence"]) if data.get("source_search_sequence") is not None else None,
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class LeadSaveResult:
    """Result of attempting to persist one discovered lead."""

    lead: LeadRecord
    saved: bool
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "lead": self.lead.as_dict(),
            "saved": self.saved,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LeadSaveResult":
        return cls(
            lead=LeadRecord.from_dict(dict(data["lead"])),
            saved=bool(data["saved"]),
            reason=str(data["reason"]),
        )


@dataclass(slots=True)
class LeadICPState:
    """Durable per-ICP progress state outside the model transcript."""

    icp: LeadICP
    status: str = "pending"
    searches: list[LeadSearchRecord] = field(default_factory=list)
    summaries: list[LeadSearchSummary] = field(default_factory=list)
    saved_lead_keys: list[str] = field(default_factory=list)
    completed_at: str | None = None

    def __post_init__(self) -> None:
        if self.status not in _ICP_STATUS_VALUES:
            allowed = ", ".join(sorted(_ICP_STATUS_VALUES))
            raise ValueError(f"LeadICPState status must be one of: {allowed}.")

    def as_dict(self) -> dict[str, Any]:
        return {
            "icp": self.icp.as_dict(),
            "status": self.status,
            "searches": [entry.as_dict() for entry in self.searches],
            "summaries": [entry.as_dict() for entry in self.summaries],
            "saved_lead_keys": list(self.saved_lead_keys),
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LeadICPState":
        return cls(
            icp=LeadICP.from_dict(dict(data["icp"])),
            status=str(data.get("status", "pending")),
            searches=[LeadSearchRecord.from_dict(item) for item in data.get("searches", [])],
            summaries=[LeadSearchSummary.from_dict(item) for item in data.get("summaries", [])],
            saved_lead_keys=[str(item) for item in data.get("saved_lead_keys", [])],
            completed_at=str(data["completed_at"]) if data.get("completed_at") else None,
        )


@runtime_checkable
class LeadsStorageBackend(Protocol):
    """Pluggable persistence layer for deterministic lead saving and dedupe."""

    def start_run(self, run_id: str, metadata: dict[str, Any]) -> None:
        ...

    def finish_run(self, run_id: str, completed_at: str) -> None:
        ...

    def save_leads(
        self,
        run_id: str,
        icp_key: str,
        leads: Sequence[LeadRecord],
        metadata: dict[str, Any] | None = None,
    ) -> tuple[LeadSaveResult, ...]:
        ...

    def has_seen_lead(self, dedupe_key: str) -> bool:
        ...

    def list_leads(self, *, icp_key: str | None = None) -> list[LeadRecord]:
        ...

    def current_run_id(self) -> str | None:
        ...


class FileSystemLeadsStorageBackend:
    """Default filesystem-backed implementation of :class:`LeadsStorageBackend`."""

    def __init__(self, memory_path: str | Path) -> None:
        self._memory_path = Path(memory_path)
        self._storage_path = self._memory_path / LEADS_STORAGE_DIRNAME
        self._run_storage = FileSystemStorageBackend(self._storage_path)
        self._saved_leads_path = self._storage_path / SAVED_LEADS_FILENAME

    def start_run(self, run_id: str, metadata: dict[str, Any]) -> None:
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._ensure_saved_leads_file()
        self._run_storage.start_run(run_id, metadata)

    def finish_run(self, run_id: str, completed_at: str) -> None:
        self._run_storage.finish_run(run_id, completed_at)

    def save_leads(
        self,
        run_id: str,
        icp_key: str,
        leads: Sequence[LeadRecord],
        metadata: dict[str, Any] | None = None,
    ) -> tuple[LeadSaveResult, ...]:
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._ensure_saved_leads_file()

        entries = self._read_saved_entries()
        seen_keys = {str(entry["dedupe_key"]) for entry in entries}
        results: list[LeadSaveResult] = []

        for lead in leads:
            dedupe_key = lead.dedupe_key()
            if dedupe_key in seen_keys:
                duplicate_result = LeadSaveResult(lead=lead, saved=False, reason="duplicate")
                results.append(duplicate_result)
                self._run_storage.log_event(
                    run_id,
                    "lead_duplicate",
                    {
                        "dedupe_key": dedupe_key,
                        "icp_key": icp_key,
                        "lead": lead.as_dict(),
                    },
                )
                continue

            persisted_entry = {
                "dedupe_key": dedupe_key,
                "icp_key": icp_key,
                "run_id": run_id,
                "saved_at": _utcnow(),
                "lead": lead.as_dict(),
                "metadata": dict(metadata or {}),
            }
            entries.append(persisted_entry)
            seen_keys.add(dedupe_key)
            saved_result = LeadSaveResult(lead=lead, saved=True, reason="saved")
            results.append(saved_result)
            self._run_storage.log_event(
                run_id,
                "lead_saved",
                {
                    "dedupe_key": dedupe_key,
                    "icp_key": icp_key,
                    "lead": lead.as_dict(),
                    "metadata": dict(metadata or {}),
                },
            )

        _write_json(self._saved_leads_path, entries)
        return tuple(results)

    def has_seen_lead(self, dedupe_key: str) -> bool:
        self._ensure_saved_leads_file()
        normalized = str(dedupe_key)
        return any(str(entry["dedupe_key"]) == normalized for entry in self._read_saved_entries())

    def list_leads(self, *, icp_key: str | None = None) -> list[LeadRecord]:
        self._ensure_saved_leads_file()
        leads: list[LeadRecord] = []
        for entry in self._read_saved_entries():
            if icp_key is not None and str(entry.get("icp_key", "")) != icp_key:
                continue
            leads.append(LeadRecord.from_dict(dict(entry["lead"])))
        return leads

    def current_run_id(self) -> str | None:
        return self._run_storage.current_run_id()

    def _ensure_saved_leads_file(self) -> None:
        if not self._saved_leads_path.exists():
            self._saved_leads_path.parent.mkdir(parents=True, exist_ok=True)
            _write_json(self._saved_leads_path, [])

    def _read_saved_entries(self) -> list[dict[str, Any]]:
        payload = _read_json_file(self._saved_leads_path, expected_type=list)
        return [dict(entry) for entry in payload]


@dataclass(slots=True)
class LeadsMemoryStore:
    """Manage durable file-backed state for a multi-ICP leads run."""

    memory_path: Path

    def __post_init__(self) -> None:
        self.memory_path = Path(self.memory_path)

    @property
    def icps_dir(self) -> Path:
        return self.memory_path / ICPS_DIRNAME

    @property
    def run_config_path(self) -> Path:
        return self.memory_path / RUN_CONFIG_FILENAME

    @property
    def run_state_path(self) -> Path:
        return self.memory_path / RUN_STATE_FILENAME

    def prepare(self) -> None:
        self.memory_path.mkdir(parents=True, exist_ok=True)
        self.icps_dir.mkdir(parents=True, exist_ok=True)

    def write_run_config(self, config: LeadRunConfig) -> None:
        self.prepare()
        _write_json(self.run_config_path, config.as_dict())

    def read_run_config(self) -> LeadRunConfig:
        data = _read_json_file(self.run_config_path, expected_type=dict)
        return LeadRunConfig.from_dict(data)

    def write_run_state(self, state: LeadRunState) -> None:
        self.prepare()
        _write_json(self.run_state_path, state.as_dict())

    def read_run_state(self) -> LeadRunState:
        data = _read_json_file(self.run_state_path, expected_type=dict)
        return LeadRunState.from_dict(data)

    def initialize_icp_states(self, icps: Sequence[LeadICP]) -> None:
        self.prepare()
        for icp in icps:
            path = self._icp_state_path(icp.key)
            if path.exists():
                continue
            _write_json(path, LeadICPState(icp=icp).as_dict())

    def read_icp_state(self, icp_key: str) -> LeadICPState:
        path = self._icp_state_path(icp_key)
        data = _read_json_file(path, expected_type=dict)
        return LeadICPState.from_dict(data)

    def write_icp_state(self, state: LeadICPState) -> None:
        self.prepare()
        _write_json(self._icp_state_path(state.icp.key), state.as_dict())

    def list_icp_states(self) -> list[LeadICPState]:
        if not self.icps_dir.exists():
            return []
        paths = sorted(self.icps_dir.glob("*.json"))
        return [LeadICPState.from_dict(_read_json_file(path, expected_type=dict)) for path in paths]

    def next_search_sequence(self, icp_key: str) -> int:
        state = self.read_icp_state(icp_key)
        last_search_sequence = state.searches[-1].sequence if state.searches else 0
        last_summary_sequence = state.summaries[-1].last_sequence or 0 if state.summaries else 0
        return max(last_search_sequence, last_summary_sequence) + 1

    def append_search(self, icp_key: str, search: LeadSearchRecord) -> LeadICPState:
        state = self.read_icp_state(icp_key)
        if search.icp_key != state.icp.key:
            raise ValueError(
                f"Search icp_key '{search.icp_key}' does not match state key '{state.icp.key}'."
            )
        state.searches.append(search)
        self.write_icp_state(state)
        return state

    def compact_searches(
        self,
        icp_key: str,
        *,
        summary_content: str,
        keep_last: int = 0,
        created_at: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> LeadSearchSummary:
        if keep_last < 0:
            raise ValueError("keep_last must be zero or greater.")
        state = self.read_icp_state(icp_key)
        replaceable = state.searches[:-keep_last] if keep_last else list(state.searches)
        if not replaceable:
            raise ValueError(f"No searchable history available to compact for ICP '{icp_key}'.")

        summary = LeadSearchSummary(
            summary_id=f"summary_{len(state.summaries) + 1}",
            icp_key=icp_key,
            created_at=created_at or _utcnow(),
            content=summary_content,
            replaced_search_count=len(replaceable),
            last_sequence=replaceable[-1].sequence,
            metadata=dict(metadata or {}),
        )
        state.summaries.append(summary)
        state.searches = state.searches[len(replaceable):]
        self.write_icp_state(state)
        return summary

    def read_search_context(
        self,
        icp_key: str,
        *,
        tail_size: int | None = None,
    ) -> tuple[tuple[LeadSearchSummary, ...], tuple[LeadSearchRecord, ...]]:
        state = self.read_icp_state(icp_key)
        if tail_size is None:
            searches = tuple(state.searches)
        else:
            if tail_size < 0:
                raise ValueError("tail_size must be zero or greater when provided.")
            searches = tuple(state.searches[-tail_size:]) if tail_size else ()
        return tuple(state.summaries), searches

    def record_saved_lead_key(self, icp_key: str, dedupe_key: str) -> LeadICPState:
        state = self.read_icp_state(icp_key)
        if dedupe_key not in state.saved_lead_keys:
            state.saved_lead_keys.append(dedupe_key)
            self.write_icp_state(state)
        return state

    def has_saved_lead_key(self, icp_key: str, dedupe_key: str) -> bool:
        state = self.read_icp_state(icp_key)
        return dedupe_key in state.saved_lead_keys

    def _icp_state_path(self, icp_key: str) -> Path:
        return self.icps_dir / f"{icp_key}.json"


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _normalize_url(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        return ""
    parts = urlsplit(stripped)
    path = parts.path.rstrip("/")
    normalized = urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))
    return normalized.lower()


def _utcnow() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _read_json_file(path: Path, *, expected_type: type) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Expected file at '{path}'.")
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        payload: Any = expected_type()
    else:
        payload = json.loads(raw)
    if not isinstance(payload, expected_type):
        raise ValueError(f"Expected JSON {expected_type.__name__} in '{path.name}'.")
    return payload


__all__ = [
    "FileSystemLeadsStorageBackend",
    "ICPS_DIRNAME",
    "LEADS_STORAGE_DIRNAME",
    "LeadICP",
    "LeadICPState",
    "LeadRecord",
    "LeadRunConfig",
    "LeadRunState",
    "LeadSaveResult",
    "LeadSearchRecord",
    "LeadSearchSummary",
    "LeadsMemoryStore",
    "LeadsStorageBackend",
    "RUN_CONFIG_FILENAME",
    "RUN_STATE_FILENAME",
    "SAVED_LEADS_FILENAME",
]
