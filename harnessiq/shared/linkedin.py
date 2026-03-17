"""Shared LinkedIn agent constants and definition-only data models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

from harnessiq.shared.agents import DEFAULT_AGENT_MAX_TOKENS, DEFAULT_AGENT_RESET_THRESHOLD

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
JOB_SEARCH_CONFIG_FILENAME = "job_search_config.json"
SCREENSHOT_DIRNAME = "screenshots"
MANAGED_FILES_DIRNAME = "managed_files"


@dataclass(frozen=True, slots=True)
class JobSearchConfig:
    """Structured LinkedIn job search configuration mirroring LinkedIn's filter UI.

    All fields are optional.  Pass ``description`` alone for a free-form fallback
    when structured filter fields are not provided.

    Valid values for ``remote_type``: ``"onsite"``, ``"remote"``, ``"hybrid"``.
    Valid values for ``experience_levels``: ``"internship"``, ``"entry"``,
    ``"associate"``, ``"mid_senior"``, ``"director"``, ``"executive"``.
    Valid values for ``date_posted``: ``"past_24_hours"``, ``"past_week"``,
    ``"past_month"``, ``"any_time"``.
    Valid values for ``job_type``: ``"full_time"``, ``"part_time"``,
    ``"contract"``, ``"temporary"``, ``"volunteer"``, ``"other"``.
    """

    title: str | None = None
    location: str | None = None
    remote_type: str | None = None
    experience_levels: tuple[str, ...] = ()
    date_posted: str | None = None
    easy_apply_only: bool = False
    salary_min: int | None = None
    salary_max: int | None = None
    job_type: tuple[str, ...] = ()
    companies: tuple[str, ...] = ()
    industries: tuple[str, ...] = ()
    description: str | None = None

    def is_empty(self) -> bool:
        """Return True when no field carries a meaningful value."""
        return not self.as_dict()

    def render(self) -> str:
        """Human-readable string suitable for injection into the agent context window."""
        lines: list[str] = []
        if self.description:
            lines.append(self.description)
            lines.append("")
        if self.title:
            lines.append(f"Title: {self.title}")
        if self.location:
            lines.append(f"Location: {self.location}")
        if self.remote_type:
            lines.append(f"Remote Type: {self.remote_type.replace('_', ' ').title()}")
        if self.experience_levels:
            formatted = ", ".join(lvl.replace("_", " ").title() for lvl in self.experience_levels)
            lines.append(f"Experience Levels: {formatted}")
        if self.date_posted:
            lines.append(f"Date Posted: {self.date_posted.replace('_', ' ').title()}")
        if self.easy_apply_only:
            lines.append("Easy Apply Only: Yes")
        if self.salary_min is not None and self.salary_max is not None:
            lines.append(f"Salary Range: ${self.salary_min:,} \u2013 ${self.salary_max:,}")
        elif self.salary_min is not None:
            lines.append(f"Salary: ${self.salary_min:,}+")
        elif self.salary_max is not None:
            lines.append(f"Salary: Up to ${self.salary_max:,}")
        if self.job_type:
            formatted = ", ".join(jt.replace("_", " ").title() for jt in self.job_type)
            lines.append(f"Job Types: {formatted}")
        if self.companies:
            lines.append(f"Companies: {', '.join(self.companies)}")
        if self.industries:
            lines.append(f"Industries: {', '.join(self.industries)}")
        return "\n".join(lines) if lines else "(job search config not set)"

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.title:
            payload["title"] = self.title
        if self.location:
            payload["location"] = self.location
        if self.remote_type:
            payload["remote_type"] = self.remote_type
        if self.experience_levels:
            payload["experience_levels"] = list(self.experience_levels)
        if self.date_posted:
            payload["date_posted"] = self.date_posted
        if self.easy_apply_only:
            payload["easy_apply_only"] = True
        if self.salary_min is not None:
            payload["salary_min"] = self.salary_min
        if self.salary_max is not None:
            payload["salary_max"] = self.salary_max
        if self.job_type:
            payload["job_type"] = list(self.job_type)
        if self.companies:
            payload["companies"] = list(self.companies)
        if self.industries:
            payload["industries"] = list(self.industries)
        if self.description:
            payload["description"] = self.description
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "JobSearchConfig":
        return cls(
            title=payload.get("title") or None,
            location=payload.get("location") or None,
            remote_type=payload.get("remote_type") or None,
            experience_levels=tuple(payload.get("experience_levels") or ()),
            date_posted=payload.get("date_posted") or None,
            easy_apply_only=bool(payload.get("easy_apply_only", False)),
            salary_min=int(payload["salary_min"]) if payload.get("salary_min") is not None else None,
            salary_max=int(payload["salary_max"]) if payload.get("salary_max") is not None else None,
            job_type=tuple(payload.get("job_type") or ()),
            companies=tuple(payload.get("companies") or ()),
            industries=tuple(payload.get("industries") or ()),
            description=payload.get("description") or None,
        )

    @classmethod
    def from_string(cls, description: str) -> "JobSearchConfig":
        """Construct a config with only a free-form description string."""
        stripped = description.strip()
        if not stripped:
            raise ValueError("Job search description must not be empty.")
        return cls(description=stripped)


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
    "JOB_SEARCH_CONFIG_FILENAME",
    "JobApplicationRecord",
    "JobSearchConfig",
    "LinkedInAgentConfig",
    "LinkedInManagedFile",
    "MANAGED_FILES_DIRNAME",
    "MANAGED_FILES_INDEX_FILENAME",
    "RUNTIME_PARAMETERS_FILENAME",
    "SCREENSHOT_DIRNAME",
    "ScreenshotPersistor",
    "USER_PROFILE_FILENAME",
]
