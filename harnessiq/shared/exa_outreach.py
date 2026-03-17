"""Shared data models, memory store, and storage backend for ExaOutreachAgent."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# File name constants
# ---------------------------------------------------------------------------

QUERY_CONFIG_FILENAME = "query_config.json"
AGENT_IDENTITY_FILENAME = "agent_identity.txt"
ADDITIONAL_PROMPT_FILENAME = "additional_prompt.txt"
RUNS_DIRNAME = "runs"

DEFAULT_AGENT_IDENTITY = (
    "A disciplined outreach specialist who finds relevant prospects via Exa neural "
    "search, selects the most appropriate email template for each lead, personalizes "
    "the message with specific details from their profile, and sends concise, "
    "value-first cold emails."
)

DEFAULT_SEARCH_QUERY = "(search query not configured)"

# ---------------------------------------------------------------------------
# EmailTemplate
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EmailTemplate:
    """A deployable cold email template with metadata for agent selection.

    Attributes:
        id: Unique identifier used to reference this template.
        title: Human-readable template name.
        subject: Email subject line.
        description: When and for whom to use this template.
        actual_email: Full email body — use ``{{name}}``, ``{{company}}`` etc. for personalization.
        links: Optional URLs to include or reference in the email.
        pain_points: Target pain points this template addresses.
        icp: Ideal customer profile this template is written for.
        extra: Open-ended additional metadata.
    """

    id: str
    title: str
    subject: str
    description: str
    actual_email: str
    links: tuple[str, ...] = ()
    pain_points: tuple[str, ...] = ()
    icp: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("EmailTemplate id must not be blank.")
        if not self.title.strip():
            raise ValueError("EmailTemplate title must not be blank.")
        if not self.subject.strip():
            raise ValueError("EmailTemplate subject must not be blank.")
        if not self.actual_email.strip():
            raise ValueError("EmailTemplate actual_email must not be blank.")

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "id": self.id,
            "title": self.title,
            "subject": self.subject,
            "description": self.description,
            "actual_email": self.actual_email,
            "links": list(self.links),
            "pain_points": list(self.pain_points),
            "icp": self.icp,
            "extra": dict(self.extra),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EmailTemplate":
        """Construct an ``EmailTemplate`` from a raw dict (e.g. parsed from JSON)."""
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            subject=str(data["subject"]),
            description=str(data.get("description", "")),
            actual_email=str(data["actual_email"]),
            links=tuple(str(v) for v in data.get("links", [])),
            pain_points=tuple(str(v) for v in data.get("pain_points", [])),
            icp=str(data.get("icp", "")),
            extra=dict(data.get("extra", {})),
        )


# ---------------------------------------------------------------------------
# LeadRecord
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class LeadRecord:
    """A prospect discovered via Exa search."""

    url: str
    name: str
    found_at: str
    email_address: str | None = None
    notes: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "name": self.name,
            "found_at": self.found_at,
            "email_address": self.email_address,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LeadRecord":
        return cls(
            url=str(data["url"]),
            name=str(data["name"]),
            found_at=str(data["found_at"]),
            email_address=str(data["email_address"]) if data.get("email_address") else None,
            notes=str(data["notes"]) if data.get("notes") else None,
        )


# ---------------------------------------------------------------------------
# EmailSentRecord
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class EmailSentRecord:
    """A record of one email sent to a prospect."""

    to_email: str
    to_name: str
    subject: str
    template_id: str
    sent_at: str
    notes: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "to_email": self.to_email,
            "to_name": self.to_name,
            "subject": self.subject,
            "template_id": self.template_id,
            "sent_at": self.sent_at,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EmailSentRecord":
        return cls(
            to_email=str(data["to_email"]),
            to_name=str(data["to_name"]),
            subject=str(data["subject"]),
            template_id=str(data["template_id"]),
            sent_at=str(data["sent_at"]),
            notes=str(data["notes"]) if data.get("notes") else None,
        )


# ---------------------------------------------------------------------------
# OutreachRunLog
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class OutreachRunLog:
    """Captures all activity from a single ExaOutreachAgent run."""

    run_id: str
    started_at: str
    query: str
    leads_found: list[LeadRecord] = field(default_factory=list)
    emails_sent: list[EmailSentRecord] = field(default_factory=list)
    completed_at: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "query": self.query,
            "leads_found": [r.as_dict() for r in self.leads_found],
            "emails_sent": [r.as_dict() for r in self.emails_sent],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OutreachRunLog":
        return cls(
            run_id=str(data["run_id"]),
            started_at=str(data["started_at"]),
            query=str(data["query"]),
            leads_found=[LeadRecord.from_dict(r) for r in data.get("leads_found", [])],
            emails_sent=[EmailSentRecord.from_dict(r) for r in data.get("emails_sent", [])],
            completed_at=str(data["completed_at"]) if data.get("completed_at") else None,
        )


# ---------------------------------------------------------------------------
# StorageBackend protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class StorageBackend(Protocol):
    """Pluggable persistence layer for ExaOutreachAgent run data.

    The default implementation is :class:`FileSystemStorageBackend`.
    Custom implementations can route to any backend (database, spreadsheet,
    CRM, etc.) by implementing this protocol.
    """

    def start_run(self, run_id: str, query: str) -> None:
        """Initialise storage for a new run before the agent loop starts."""
        ...

    def finish_run(self, run_id: str, completed_at: str) -> None:
        """Mark a run as complete after the agent loop exits."""
        ...

    def log_lead(self, run_id: str, lead: LeadRecord) -> None:
        """Persist a newly discovered lead.  Called deterministically inside the tool handler."""
        ...

    def log_email_sent(self, run_id: str, record: EmailSentRecord) -> None:
        """Persist a sent email record.  Called deterministically inside the tool handler."""
        ...

    def is_contacted(self, url: str) -> bool:
        """Return True if the Exa profile URL has appeared in any prior run."""
        ...

    def current_run_id(self) -> str | None:
        """Return the active run ID, or None if no run has been started."""
        ...


# ---------------------------------------------------------------------------
# FileSystemStorageBackend
# ---------------------------------------------------------------------------


class FileSystemStorageBackend:
    """Default :class:`StorageBackend` that writes ``run_N.json`` files to disk.

    Each run gets its own file under ``memory_path/runs/run_N.json``.
    The run number N is the next integer after the highest existing run file.
    ``is_contacted`` scans all existing run files for a matching URL.
    """

    def __init__(self, memory_path: Path) -> None:
        self._memory_path = Path(memory_path)
        self._runs_dir = self._memory_path / RUNS_DIRNAME
        self._current_run_id: str | None = None
        self._current_run_path: Path | None = None

    # ------------------------------------------------------------------
    # StorageBackend implementation
    # ------------------------------------------------------------------

    def start_run(self, run_id: str, query: str) -> None:
        self._runs_dir.mkdir(parents=True, exist_ok=True)
        self._current_run_id = run_id
        run_log = OutreachRunLog(
            run_id=run_id,
            started_at=_utcnow(),
            query=query,
        )
        path = self._run_path(run_id)
        self._current_run_path = path
        _write_json(path, run_log.as_dict())

    def finish_run(self, run_id: str, completed_at: str) -> None:
        path = self._run_path(run_id)
        run_log = self._read_run_log(path)
        run_log.completed_at = completed_at
        _write_json(path, run_log.as_dict())

    def log_lead(self, run_id: str, lead: LeadRecord) -> None:
        path = self._run_path(run_id)
        run_log = self._read_run_log(path)
        run_log.leads_found.append(lead)
        _write_json(path, run_log.as_dict())

    def log_email_sent(self, run_id: str, record: EmailSentRecord) -> None:
        path = self._run_path(run_id)
        run_log = self._read_run_log(path)
        run_log.emails_sent.append(record)
        _write_json(path, run_log.as_dict())

    def is_contacted(self, url: str) -> bool:
        if not self._runs_dir.exists():
            return False
        for run_path in self._list_run_paths():
            try:
                run_log = self._read_run_log(run_path)
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
            for lead in run_log.leads_found:
                if lead.url == url:
                    return True
        return False

    def current_run_id(self) -> str | None:
        return self._current_run_id

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_path(self, run_id: str) -> Path:
        return self._runs_dir / f"{run_id}.json"

    def _read_run_log(self, path: Path) -> OutreachRunLog:
        data = json.loads(path.read_text(encoding="utf-8"))
        return OutreachRunLog.from_dict(data)

    def _list_run_paths(self) -> list[Path]:
        """Return run JSON files sorted by run number ascending."""
        paths = list(self._runs_dir.glob("run_*.json"))
        return sorted(paths, key=_run_file_sort_key)


# ---------------------------------------------------------------------------
# ExaOutreachMemoryStore
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ExaOutreachMemoryStore:
    """Manage the durable state files used by the ExaOutreach harness."""

    memory_path: Path

    def __post_init__(self) -> None:
        self.memory_path = Path(self.memory_path)

    @property
    def query_config_path(self) -> Path:
        return self.memory_path / QUERY_CONFIG_FILENAME

    @property
    def agent_identity_path(self) -> Path:
        return self.memory_path / AGENT_IDENTITY_FILENAME

    @property
    def additional_prompt_path(self) -> Path:
        return self.memory_path / ADDITIONAL_PROMPT_FILENAME

    @property
    def runs_dir(self) -> Path:
        return self.memory_path / RUNS_DIRNAME

    def prepare(self) -> None:
        """Create the memory directory structure and initialise default files."""
        self.memory_path.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        _ensure_json_file(self.query_config_path, {})
        _ensure_text_file(self.agent_identity_path, DEFAULT_AGENT_IDENTITY)
        _ensure_text_file(self.additional_prompt_path, "")

    def next_run_id(self) -> str:
        """Return the next sequential run ID (e.g. ``run_1``, ``run_2``, ...)."""
        existing = self.list_run_files()
        return f"run_{len(existing) + 1}"

    def list_run_files(self) -> list[Path]:
        """Return run JSON files sorted by run number ascending."""
        if not self.runs_dir.exists():
            return []
        paths = list(self.runs_dir.glob("run_*.json"))
        return sorted(paths, key=_run_file_sort_key)

    def read_run(self, run_id: str) -> OutreachRunLog:
        """Read and return a run log by run ID."""
        path = self.runs_dir / f"{run_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Run file for '{run_id}' not found at '{path}'.")
        data = json.loads(path.read_text(encoding="utf-8"))
        return OutreachRunLog.from_dict(data)

    def read_query_config(self) -> dict[str, Any]:
        return _read_json_file(self.query_config_path, expected_type=dict)

    def write_query_config(self, config: dict[str, Any]) -> None:
        _write_json(self.query_config_path, config)

    def read_agent_identity(self) -> str:
        return self.agent_identity_path.read_text(encoding="utf-8").strip()

    def write_agent_identity(self, text: str) -> None:
        _write_text(self.agent_identity_path, text)

    def read_additional_prompt(self) -> str:
        return self.additional_prompt_path.read_text(encoding="utf-8").strip()

    def write_additional_prompt(self, text: str) -> None:
        _write_text(self.additional_prompt_path, text)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    rendered = text if not text or text.endswith("\n") else f"{text}\n"
    path.write_text(rendered, encoding="utf-8")


def _ensure_json_file(path: Path, default_payload: Any) -> None:
    if not path.exists():
        _write_json(path, default_payload)


def _ensure_text_file(path: Path, default_content: str) -> None:
    if not path.exists():
        path.write_text(default_content, encoding="utf-8")


def _read_json_file(path: Path, *, expected_type: type) -> Any:
    if not path.exists():
        return expected_type()
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return expected_type()
    payload = json.loads(raw)
    if not isinstance(payload, expected_type):
        raise ValueError(f"Expected JSON {expected_type.__name__} in '{path.name}'.")
    return payload


def _run_file_sort_key(path: Path) -> int:
    """Extract the run number from ``run_N.json`` for deterministic sorting."""
    match = re.search(r"run_(\d+)\.json$", path.name)
    return int(match.group(1)) if match else 0


__all__ = [
    "ADDITIONAL_PROMPT_FILENAME",
    "AGENT_IDENTITY_FILENAME",
    "DEFAULT_AGENT_IDENTITY",
    "DEFAULT_SEARCH_QUERY",
    "EmailSentRecord",
    "EmailTemplate",
    "ExaOutreachMemoryStore",
    "FileSystemStorageBackend",
    "LeadRecord",
    "OutreachRunLog",
    "QUERY_CONFIG_FILENAME",
    "RUNS_DIRNAME",
    "StorageBackend",
]
