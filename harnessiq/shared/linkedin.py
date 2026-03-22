"""Shared LinkedIn agent constants and definition-only data models."""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol

from harnessiq.shared.agents import DEFAULT_AGENT_MAX_TOKENS, DEFAULT_AGENT_RESET_THRESHOLD
from harnessiq.shared.harness_manifest import HarnessManifest, HarnessMemoryFileSpec, HarnessParameterSpec

DEFAULT_AGENT_IDENTITY = (
    "You are a meticulous, high-throughput LinkedIn job application specialist with deep familiarity with "
    "LinkedIn's UI, its filter system, its Easy Apply multi-step forms, and the full spectrum of edge cases "
    "encountered when automating browser-based job applications. You have processed thousands of job listings "
    "and submitted hundreds of applications, which means you know exactly what a 'Software Engineer II' title "
    "means relative to the user's target seniority, you know when a salary range is genuinely within the "
    "user's band versus just barely touching it, and you know when a job description is a near-perfect match "
    "versus a marginal one the user would want to skip. You do not treat job matching as a keyword problem — "
    "you treat it as a judgment call, and you make that call with the same discernment that a thoughtful "
    "recruiter would.\n\n"
    "You are a precise browser operator. You never take a shot at a selector that might match something else "
    "on the page. Before clicking a button, you confirm what it does. Before typing into an input, you confirm "
    "it is the right field. Before submitting a form step, you review what you have entered. You understand that "
    "browser automation is stateful and that a wrong click can send you down a navigation path that is difficult "
    "to recover from, so you build verification checkpoints into your actions — taking screenshots and reading "
    "page state before committing to irreversible sequences. You treat every navigation, form interaction, and "
    "submission as a logged, inspectable, recoverable operation.\n\n"
    "You handle the user's data with absolute fidelity. When a form asks for the user's phone number, email, "
    "years of experience, education level, or any other personal detail, you draw exclusively from the User "
    "Profile section. You never invent a plausible-sounding answer. You never skip a required field by entering "
    "a placeholder. If the user's profile does not contain the information a form is requesting, you stop, log "
    "the specific gap, and mark the application as requiring user intervention rather than submit an application "
    "with fabricated personal data. The user's professional reputation is at stake in every submission.\n\n"
    "You maintain state with precision across every action. Every job you apply to, skip, or fail to apply to "
    "gets recorded immediately — before you navigate away. Every meaningful browser action gets a corresponding "
    "action log entry. You treat your memory system as the authoritative record of what has happened, and you "
    "trust it absolutely: if a job_id appears in applied_jobs.jsonl under any status, you do not apply again "
    "regardless of what you see on screen. You never accumulate unlogged state. If a context reset occurs "
    "mid-session, you reconstruct exactly where you were from the parameter sections alone and continue "
    "without missing a beat."
)
DEFAULT_JOB_PREFERENCES = "Describe the target job title, level, location, compensation, remote preference, and exclusions."
DEFAULT_USER_PROFILE = "Add resume highlights, skills, work authorization, and any reusable application answers."
DEFAULT_LINKEDIN_START_URL = "https://www.linkedin.com/jobs/"
DEFAULT_LINKEDIN_ACTION_LOG_WINDOW = 10
DEFAULT_LINKEDIN_NOTIFY_ON_PAUSE = True

APPLIED_JOBS_FILENAME = "applied_jobs.jsonl"
ACTION_LOG_FILENAME = "action_log.jsonl"
JOB_PREFERENCES_FILENAME = "job_preferences.md"
USER_PROFILE_FILENAME = "user_profile.md"
AGENT_IDENTITY_FILENAME = "agent_identity.md"
RUNTIME_PARAMETERS_FILENAME = "runtime_parameters.json"
CUSTOM_PARAMETERS_FILENAME = "custom_parameters.json"
ADDITIONAL_PROMPT_FILENAME = "additional_prompt.md"
MANAGED_FILES_INDEX_FILENAME = "managed_files.json"
SCREENSHOT_DIRNAME = "screenshots"
MANAGED_FILES_DIRNAME = "managed_files"


@dataclass(frozen=True, slots=True)
class LinkedInAgentConfig:
    """Configuration for the LinkedIn job application harness."""

    memory_path: Path
    max_tokens: int = DEFAULT_AGENT_MAX_TOKENS
    reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD
    action_log_window: int = DEFAULT_LINKEDIN_ACTION_LOG_WINDOW
    linkedin_start_url: str = DEFAULT_LINKEDIN_START_URL
    notify_on_pause: bool = DEFAULT_LINKEDIN_NOTIFY_ON_PAUSE
    pause_webhook: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "memory_path", Path(self.memory_path))
        if self.action_log_window <= 0:
            message = "action_log_window must be greater than zero."
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class JobApplicationRecord:
    """Append-only record describing the state of a LinkedIn job application."""

    job_id: str
    title: str
    company: str
    url: str
    applied_at: str
    status: str
    easy_apply: bool | None = None
    notes: str | None = None
    updated_at: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return {key: value for key, value in payload.items() if value is not None}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "JobApplicationRecord":
        return cls(
            job_id=str(payload["job_id"]),
            title=str(payload["title"]),
            company=str(payload["company"]),
            url=str(payload["url"]),
            applied_at=str(payload["applied_at"]),
            status=str(payload["status"]),
            easy_apply=payload.get("easy_apply"),
            notes=str(payload["notes"]) if payload.get("notes") is not None else None,
            updated_at=str(payload["updated_at"]) if payload.get("updated_at") is not None else None,
        )


@dataclass(frozen=True, slots=True)
class ActionLogEntry:
    """Append-only semantic action log entry."""

    timestamp: str
    action: str
    result: str

    def as_dict(self) -> dict[str, str]:
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "result": self.result,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ActionLogEntry":
        return cls(
            timestamp=str(payload["timestamp"]),
            action=str(payload["action"]),
            result=str(payload["result"]),
        )


@dataclass(frozen=True, slots=True)
class LinkedInManagedFile:
    """Metadata describing a CLI-managed file stored in agent memory."""

    name: str
    relative_path: str
    source_path: str | None = None
    created_at: str | None = None
    kind: str = "file"

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return {key: value for key, value in payload.items() if value is not None}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LinkedInManagedFile":
        return cls(
            name=str(payload["name"]),
            relative_path=str(payload["relative_path"]),
            source_path=str(payload["source_path"]) if payload.get("source_path") is not None else None,
            created_at=str(payload["created_at"]) if payload.get("created_at") is not None else None,
            kind=str(payload.get("kind", "file")),
        )


@dataclass(slots=True)
class LinkedInMemoryStore:
    """Manage the durable state files used by the LinkedIn harness."""

    memory_path: Path
    action_log_window: int = DEFAULT_LINKEDIN_ACTION_LOG_WINDOW

    def __post_init__(self) -> None:
        self.memory_path = Path(self.memory_path)

    @property
    def job_preferences_path(self) -> Path:
        return self.memory_path / JOB_PREFERENCES_FILENAME

    @property
    def user_profile_path(self) -> Path:
        return self.memory_path / USER_PROFILE_FILENAME

    @property
    def agent_identity_path(self) -> Path:
        return self.memory_path / AGENT_IDENTITY_FILENAME

    @property
    def runtime_parameters_path(self) -> Path:
        return self.memory_path / RUNTIME_PARAMETERS_FILENAME

    @property
    def custom_parameters_path(self) -> Path:
        return self.memory_path / CUSTOM_PARAMETERS_FILENAME

    @property
    def additional_prompt_path(self) -> Path:
        return self.memory_path / ADDITIONAL_PROMPT_FILENAME

    @property
    def applied_jobs_path(self) -> Path:
        return self.memory_path / APPLIED_JOBS_FILENAME

    @property
    def action_log_path(self) -> Path:
        return self.memory_path / ACTION_LOG_FILENAME

    @property
    def screenshot_dir(self) -> Path:
        return self.memory_path / SCREENSHOT_DIRNAME

    @property
    def managed_files_dir(self) -> Path:
        return self.memory_path / MANAGED_FILES_DIRNAME

    @property
    def managed_files_index_path(self) -> Path:
        return self.memory_path / MANAGED_FILES_INDEX_FILENAME

    def prepare(self) -> None:
        self.memory_path.mkdir(parents=True, exist_ok=True)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.managed_files_dir.mkdir(parents=True, exist_ok=True)
        _ensure_text_file(self.job_preferences_path, DEFAULT_JOB_PREFERENCES)
        _ensure_text_file(self.user_profile_path, DEFAULT_USER_PROFILE)
        _ensure_text_file(self.agent_identity_path, DEFAULT_AGENT_IDENTITY)
        _ensure_json_file(self.runtime_parameters_path, {})
        _ensure_json_file(self.custom_parameters_path, {})
        _ensure_text_file(self.additional_prompt_path, "")
        _ensure_json_file(self.managed_files_index_path, [])
        _ensure_text_file(self.applied_jobs_path, "")
        _ensure_text_file(self.action_log_path, "")

    def read_job_preferences(self) -> str:
        return self.job_preferences_path.read_text(encoding="utf-8").strip()

    def write_job_preferences(self, content: str) -> Path:
        return self._write_text(self.job_preferences_path, content)

    def read_user_profile(self) -> str:
        return self.user_profile_path.read_text(encoding="utf-8").strip()

    def write_user_profile(self, content: str) -> Path:
        return self._write_text(self.user_profile_path, content)

    def read_agent_identity(self) -> str:
        return self.agent_identity_path.read_text(encoding="utf-8").strip()

    def write_agent_identity(self, content: str) -> Path:
        return self._write_text(self.agent_identity_path, content)

    def read_runtime_parameters(self) -> dict[str, Any]:
        return self._read_json_file(self.runtime_parameters_path, expected_type=dict)

    def write_runtime_parameters(self, parameters: Mapping[str, Any]) -> Path:
        return self._write_json_file(self.runtime_parameters_path, dict(parameters))

    def read_custom_parameters(self) -> dict[str, Any]:
        return self._read_json_file(self.custom_parameters_path, expected_type=dict)

    def write_custom_parameters(self, parameters: Mapping[str, Any]) -> Path:
        return self._write_json_file(self.custom_parameters_path, dict(parameters))

    def read_additional_prompt(self) -> str:
        return self.additional_prompt_path.read_text(encoding="utf-8").strip()

    def write_additional_prompt(self, content: str) -> Path:
        return self._write_text(self.additional_prompt_path, content)

    def read_applied_jobs_raw(self) -> str:
        return self.applied_jobs_path.read_text(encoding="utf-8").strip()

    def read_managed_files(self) -> list[LinkedInManagedFile]:
        payload = self._read_json_file(self.managed_files_index_path, expected_type=list)
        return [LinkedInManagedFile.from_dict(entry) for entry in payload]

    def ingest_managed_file(self, source_path: str | Path, *, target_name: str | None = None) -> LinkedInManagedFile:
        self.prepare()
        source = Path(source_path).expanduser().resolve()
        if not source.exists() or not source.is_file():
            message = f"Managed file source '{source}' does not exist or is not a file."
            raise FileNotFoundError(message)
        target_filename = _sanitize_filename(target_name or source.name)
        target_path = self.managed_files_dir / target_filename
        shutil.copy2(source, target_path)
        record = LinkedInManagedFile(
            name=target_filename,
            relative_path=_relative_path_text(target_path, self.memory_path),
            source_path=str(source),
            created_at=_utcnow(),
            kind="copied_file",
        )
        self._upsert_managed_file(record)
        return record

    def write_managed_text_file(
        self,
        *,
        name: str,
        content: str,
        source_path: str | None = None,
    ) -> LinkedInManagedFile:
        self.prepare()
        target_filename = _sanitize_filename(name)
        target_path = self.managed_files_dir / target_filename
        target_path.write_text(content, encoding="utf-8")
        record = LinkedInManagedFile(
            name=target_filename,
            relative_path=_relative_path_text(target_path, self.memory_path),
            source_path=source_path,
            created_at=_utcnow(),
            kind="inline_text",
        )
        self._upsert_managed_file(record)
        return record

    def read_memory_file(self, filename: str) -> str:
        requested_path = (self.memory_path / filename).resolve()
        root_path = self.memory_path.resolve()
        if root_path not in requested_path.parents and requested_path != root_path:
            message = f"Memory file '{filename}' is outside the configured memory path."
            raise ValueError(message)
        return requested_path.read_text(encoding="utf-8")

    def append_action(self, action: str, result: str) -> ActionLogEntry:
        entry = ActionLogEntry(timestamp=_utcnow(), action=action, result=result)
        self._append_jsonl(self.action_log_path, entry.as_dict())
        return entry

    def append_job_record(self, record: JobApplicationRecord) -> JobApplicationRecord:
        self._append_jsonl(self.applied_jobs_path, record.as_dict())
        return record

    def already_applied(self, job_id: str) -> JobApplicationRecord | None:
        return self.current_jobs().get(job_id)

    def mark_job_skipped(
        self,
        *,
        job_id: str,
        title: str,
        company: str,
        url: str,
        reason: str,
    ) -> JobApplicationRecord:
        record = JobApplicationRecord(
            job_id=job_id,
            title=title,
            company=company,
            url=url,
            applied_at=_utcnow(),
            status="skipped",
            notes=reason,
        )
        return self.append_job_record(record)

    def update_job_status(self, job_id: str, status: str, notes: str) -> JobApplicationRecord:
        current_record = self.current_jobs().get(job_id)
        if current_record is None:
            message = f"Job '{job_id}' does not exist in applied_jobs.jsonl."
            raise ValueError(message)
        updated_record = JobApplicationRecord(
            job_id=current_record.job_id,
            title=current_record.title,
            company=current_record.company,
            url=current_record.url,
            applied_at=current_record.applied_at,
            status=status,
            easy_apply=current_record.easy_apply,
            notes=notes,
            updated_at=_utcnow(),
        )
        return self.append_job_record(updated_record)

    def read_applied_jobs(self) -> list[JobApplicationRecord]:
        return [JobApplicationRecord.from_dict(payload) for payload in self._read_jsonl(self.applied_jobs_path)]

    def current_jobs(self) -> dict[str, JobApplicationRecord]:
        records: dict[str, JobApplicationRecord] = {}
        for record in self.read_applied_jobs():
            records[record.job_id] = record
        return records

    def read_recent_actions(self) -> list[ActionLogEntry]:
        entries = [ActionLogEntry.from_dict(payload) for payload in self._read_jsonl(self.action_log_path)]
        return entries[-self.action_log_window :]

    def _append_jsonl(self, path: Path, payload: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True))
            handle.write("\n")

    def _write_text(self, path: Path, content: str) -> Path:
        rendered = content if not content or content.endswith("\n") else f"{content}\n"
        path.write_text(rendered, encoding="utf-8")
        return path

    def _write_json_file(self, path: Path, payload: Any) -> Path:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def _read_json_file(self, path: Path, *, expected_type: type[dict] | type[list]) -> Any:
        if not path.exists():
            return expected_type()
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return expected_type()
        payload = json.loads(raw)
        if not isinstance(payload, expected_type):
            message = f"Expected JSON {expected_type.__name__} in '{path.name}'."
            raise ValueError(message)
        return payload

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        entries: list[dict[str, Any]] = []
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            entries.append(json.loads(line))
        return entries

    def _upsert_managed_file(self, record: LinkedInManagedFile) -> None:
        managed_files = self.read_managed_files()
        indexed = {item.relative_path: item for item in managed_files}
        indexed[record.relative_path] = record
        ordered = [indexed[key].as_dict() for key in sorted(indexed)]
        self._write_json_file(self.managed_files_index_path, ordered)


class ScreenshotPersistor(Protocol):
    """Save the current browser screenshot to the provided path."""

    def __call__(self, output_path: Path, label: str) -> None:
        """Persist the current screenshot to ``output_path``."""


LINKEDIN_HARNESS_MANIFEST = HarnessManifest(
    manifest_id="linkedin",
    agent_name="linkedin_job_applier",
    display_name="LinkedIn Job Applier",
    module_path="harnessiq.agents.linkedin",
    class_name="LinkedInJobApplierAgent",
    cli_command="linkedin",
    cli_adapter_path="harnessiq.cli.platform_adapters:LinkedInHarnessCliAdapter",
    default_memory_root="memory/linkedin",
    prompt_path="harnessiq/agents/linkedin/prompts/master_prompt.md",
    runtime_parameters=(
        HarnessParameterSpec("max_tokens", "integer", "Maximum model context budget for the harness.", default=DEFAULT_AGENT_MAX_TOKENS),
        HarnessParameterSpec("reset_threshold", "number", "Fraction of max_tokens that triggers a reset.", default=DEFAULT_AGENT_RESET_THRESHOLD),
        HarnessParameterSpec("action_log_window", "integer", "Number of recent actions injected into context.", default=DEFAULT_LINKEDIN_ACTION_LOG_WINDOW),
        HarnessParameterSpec("linkedin_start_url", "string", "Initial LinkedIn jobs URL used by the harness.", default=DEFAULT_LINKEDIN_START_URL),
        HarnessParameterSpec("notify_on_pause", "boolean", "Whether pause events should emit notifications.", default=DEFAULT_LINKEDIN_NOTIFY_ON_PAUSE),
        HarnessParameterSpec("pause_webhook", "string", "Optional webhook URL for pause notifications.", nullable=True, default=None),
    ),
    custom_parameters_open_ended=True,
    memory_files=(
        HarnessMemoryFileSpec("job_preferences", JOB_PREFERENCES_FILENAME, "Durable job preference prompt block.", format="markdown"),
        HarnessMemoryFileSpec("user_profile", USER_PROFILE_FILENAME, "Durable user profile prompt block.", format="markdown"),
        HarnessMemoryFileSpec("agent_identity", AGENT_IDENTITY_FILENAME, "Override for the LinkedIn system identity.", format="markdown"),
        HarnessMemoryFileSpec("runtime_parameters", RUNTIME_PARAMETERS_FILENAME, "Persisted typed runtime overrides.", format="json"),
        HarnessMemoryFileSpec("custom_parameters", CUSTOM_PARAMETERS_FILENAME, "Open-ended user custom parameter payload.", format="json"),
        HarnessMemoryFileSpec("additional_prompt", ADDITIONAL_PROMPT_FILENAME, "Additional free-form prompt data.", format="markdown"),
        HarnessMemoryFileSpec("applied_jobs", APPLIED_JOBS_FILENAME, "Append-only job application records.", format="jsonl"),
        HarnessMemoryFileSpec("action_log", ACTION_LOG_FILENAME, "Append-only semantic action log.", format="jsonl"),
        HarnessMemoryFileSpec("managed_files_index", MANAGED_FILES_INDEX_FILENAME, "Index of CLI-managed memory files.", format="json"),
        HarnessMemoryFileSpec("managed_files", MANAGED_FILES_DIRNAME, "Durable imported or inline-managed files.", kind="directory", format="directory"),
        HarnessMemoryFileSpec("screenshots", SCREENSHOT_DIRNAME, "Persisted screenshots captured during browser runs.", kind="directory", format="directory"),
    ),
    provider_families=("playwright",),
    output_schema={
        "type": "object",
        "properties": {
            "jobs_applied": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
            "managed_files": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
            "recent_actions": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
        },
        "additionalProperties": False,
    },
)

SUPPORTED_LINKEDIN_RUNTIME_PARAMETERS = LINKEDIN_HARNESS_MANIFEST.runtime_parameter_names


def normalize_linkedin_runtime_parameters(parameters: Mapping[str, Any]) -> dict[str, Any]:
    return LINKEDIN_HARNESS_MANIFEST.coerce_runtime_parameters(parameters)


def _ensure_text_file(path: Path, default_content: str) -> None:
    if path.exists():
        return
    path.write_text(default_content, encoding="utf-8")


def _ensure_json_file(path: Path, default_payload: Any) -> None:
    if path.exists():
        return
    path.write_text(json.dumps(default_payload, indent=2, sort_keys=True), encoding="utf-8")


def _sanitize_filename(filename: str) -> str:
    candidate = Path(filename).name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", candidate).strip("-")
    if not cleaned:
        raise ValueError("Managed filenames must contain at least one alphanumeric character.")
    return cleaned


def _relative_path_text(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _coerce_int(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("Boolean values are not valid integer runtime parameters.")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        return int(value)
    raise ValueError("Runtime parameter must be an integer.")


def _coerce_float(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("Boolean values are not valid float runtime parameters.")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        return float(value)
    raise ValueError("Runtime parameter must be a float.")


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    raise ValueError("Runtime parameter must be a boolean.")


def _coerce_string(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Runtime parameter must be a non-empty string.")
    return value


def _coerce_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    raise ValueError("Runtime parameter must be a string or null.")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = [
    "ACTION_LOG_FILENAME",
    "ADDITIONAL_PROMPT_FILENAME",
    "AGENT_IDENTITY_FILENAME",
    "APPLIED_JOBS_FILENAME",
    "ActionLogEntry",
    "CUSTOM_PARAMETERS_FILENAME",
    "DEFAULT_AGENT_IDENTITY",
    "DEFAULT_JOB_PREFERENCES",
    "DEFAULT_LINKEDIN_ACTION_LOG_WINDOW",
    "DEFAULT_LINKEDIN_NOTIFY_ON_PAUSE",
    "DEFAULT_LINKEDIN_START_URL",
    "DEFAULT_USER_PROFILE",
    "JOB_PREFERENCES_FILENAME",
    "JobApplicationRecord",
    "LINKEDIN_HARNESS_MANIFEST",
    "LinkedInAgentConfig",
    "LinkedInManagedFile",
    "LinkedInMemoryStore",
    "MANAGED_FILES_DIRNAME",
    "MANAGED_FILES_INDEX_FILENAME",
    "RUNTIME_PARAMETERS_FILENAME",
    "SCREENSHOT_DIRNAME",
    "ScreenshotPersistor",
    "SUPPORTED_LINKEDIN_RUNTIME_PARAMETERS",
    "USER_PROFILE_FILENAME",
    "normalize_linkedin_runtime_parameters",
]
