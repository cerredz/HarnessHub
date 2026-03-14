"""Shared LinkedIn agent constants and definition-only data models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

from harnessiq.shared.agents import DEFAULT_AGENT_MAX_TOKENS, DEFAULT_AGENT_RESET_THRESHOLD

DEFAULT_AGENT_IDENTITY = """A focused, methodical job application assistant with browser automation capabilities.
It reads job listings carefully, applies only to roles that match the user's criteria, and preserves durable state
so context resets never lose progress."""
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

    def as_dict(self) -> dict[str, str]:
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


class ScreenshotPersistor(Protocol):
    """Save the current browser screenshot to the provided path."""

    def __call__(self, output_path: Path, label: str) -> None:
        """Persist the current screenshot to ``output_path``."""


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
    "LinkedInAgentConfig",
    "LinkedInManagedFile",
    "MANAGED_FILES_DIRNAME",
    "MANAGED_FILES_INDEX_FILENAME",
    "RUNTIME_PARAMETERS_FILENAME",
    "SCREENSHOT_DIRNAME",
    "ScreenshotPersistor",
    "USER_PROFILE_FILENAME",
]
