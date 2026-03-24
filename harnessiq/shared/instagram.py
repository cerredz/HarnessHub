"""Shared data models, memory store, and runtime helpers for Instagram discovery."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, Sequence, runtime_checkable

from harnessiq.shared.agents import DEFAULT_AGENT_MAX_TOKENS, DEFAULT_AGENT_RESET_THRESHOLD
from harnessiq.shared.harness_manifest import HarnessManifest, HarnessMemoryFileSpec, HarnessParameterSpec

ICP_PROFILES_FILENAME = "icp_profiles.json"
SEARCH_HISTORY_FILENAME = "search_history.json"
LEAD_DATABASE_FILENAME = "lead_database.json"
RUNTIME_PARAMETERS_FILENAME = "runtime_parameters.json"
AGENT_IDENTITY_FILENAME = "agent_identity.txt"
ADDITIONAL_PROMPT_FILENAME = "additional_prompt.txt"
INSTAGRAM_GOOGLE_SEARCH_URL = "https://www.google.com/search"
DEFAULT_INSTAGRAM_BROWSER_CHANNEL = "chrome"
DEFAULT_INSTAGRAM_HEADLESS = False
DEFAULT_INSTAGRAM_TIMEOUT_MS = 30_000
DEFAULT_INSTAGRAM_NETWORK_IDLE_TIMEOUT_MS = 5_000
DEFAULT_INSTAGRAM_BROWSER_VIEWPORT = {"width": 1280, "height": 900}
DEFAULT_INSTAGRAM_BROWSER_LAUNCH_ARGS = ("--disable-blink-features=AutomationControlled",)
DEFAULT_INSTAGRAM_BROWSER_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
window.chrome = window.chrome || { runtime: {} };
"""

DEFAULT_RECENT_SEARCH_WINDOW = 10
DEFAULT_RECENT_RESULT_WINDOW = 10
DEFAULT_SEARCH_RESULT_LIMIT = 5

DEFAULT_AGENT_IDENTITY = (
    "A deterministic Instagram creator discovery agent that turns ICP descriptions into concise "
    "Google search keywords, runs targeted spaced site:instagram Google searches, extracts public "
    "emails from Google result snippets, and persists every verified discovery to durable memory."
)

_EMAIL_PATTERN = re.compile(
    r"[A-Z0-9._%+-]+\s*@\s*(?:[A-Z0-9-]+\s*\.(?!\s))+[A-Z]{2,63}\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class InstagramKeywordAgentConfig:
    """Runtime configuration for the Instagram keyword discovery agent."""

    memory_path: Path
    max_tokens: int = DEFAULT_AGENT_MAX_TOKENS
    reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD
    recent_search_window: int = DEFAULT_RECENT_SEARCH_WINDOW
    recent_result_window: int = DEFAULT_RECENT_RESULT_WINDOW
    search_result_limit: int = DEFAULT_SEARCH_RESULT_LIMIT

    def __post_init__(self) -> None:
        object.__setattr__(self, "memory_path", Path(self.memory_path))
        if self.recent_search_window <= 0:
            raise ValueError("recent_search_window must be positive.")
        if self.recent_result_window <= 0:
            raise ValueError("recent_result_window must be positive.")
        if self.search_result_limit <= 0:
            raise ValueError("search_result_limit must be positive.")


@dataclass(frozen=True, slots=True)
class InstagramLeadRecord:
    """Canonical persisted record for a discovered Instagram lead."""

    source_url: str
    source_keyword: str
    found_at: str
    emails: tuple[str, ...]
    title: str = ""
    snippet: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_url", self.source_url.strip())
        object.__setattr__(self, "source_keyword", self.source_keyword.strip())
        object.__setattr__(self, "title", self.title.strip())
        object.__setattr__(self, "snippet", self.snippet.strip())
        object.__setattr__(self, "emails", tuple(_dedupe_emails(self.emails)))

    def as_dict(self) -> dict[str, Any]:
        return {
            "emails": list(self.emails),
            "found_at": self.found_at,
            "snippet": self.snippet,
            "source_keyword": self.source_keyword,
            "source_url": self.source_url,
            "title": self.title,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InstagramLeadRecord":
        return cls(
            source_url=str(data["source_url"]),
            source_keyword=str(data.get("source_keyword", "")),
            found_at=str(data["found_at"]),
            emails=tuple(str(value) for value in data.get("emails", ())),
            title=str(data.get("title", "")),
            snippet=str(data.get("snippet", "")),
        )


@dataclass(frozen=True, slots=True)
class InstagramSearchRecord:
    """Summary of one deterministic keyword search execution."""

    keyword: str
    query: str
    searched_at: str
    visited_urls: tuple[str, ...] = ()
    lead_count: int = 0
    email_count: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "keyword", self.keyword.strip())
        object.__setattr__(self, "query", self.query.strip())
        object.__setattr__(self, "visited_urls", tuple(_dedupe_strings(self.visited_urls)))

    def as_dict(self) -> dict[str, Any]:
        return {
            "email_count": self.email_count,
            "keyword": self.keyword,
            "lead_count": self.lead_count,
            "query": self.query,
            "searched_at": self.searched_at,
            "visited_urls": list(self.visited_urls),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InstagramSearchRecord":
        return cls(
            keyword=str(data["keyword"]),
            query=str(data["query"]),
            searched_at=str(data["searched_at"]),
            visited_urls=tuple(str(value) for value in data.get("visited_urls", ())),
            lead_count=int(data.get("lead_count", 0)),
            email_count=int(data.get("email_count", 0)),
        )


@dataclass(frozen=True, slots=True)
class InstagramLeadDatabase:
    """Canonical persisted lead/email store."""

    leads: tuple[InstagramLeadRecord, ...] = ()
    emails: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "emails": list(self.emails),
            "leads": [lead.as_dict() for lead in self.leads],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InstagramLeadDatabase":
        return cls(
            leads=tuple(InstagramLeadRecord.from_dict(item) for item in data.get("leads", ())),
            emails=tuple(str(value) for value in data.get("emails", ())),
        )


@dataclass(frozen=True, slots=True)
class LeadMergeSummary:
    """Summary payload returned after canonical lead persistence."""

    new_emails: int
    new_leads: int
    total_emails: int
    total_leads: int
    updated_leads: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "new_emails": self.new_emails,
            "new_leads": self.new_leads,
            "total_emails": self.total_emails,
            "total_leads": self.total_leads,
            "updated_leads": self.updated_leads,
        }


@dataclass(frozen=True, slots=True)
class InstagramSearchExecution:
    """Output returned by a deterministic browser-backed search backend."""

    search_record: InstagramSearchRecord
    leads: tuple[InstagramLeadRecord, ...] = ()


@runtime_checkable
class InstagramSearchBackend(Protocol):
    """Deterministic backend that executes one keyword search and extracts leads."""

    def search_keyword(self, *, keyword: str, max_results: int) -> InstagramSearchExecution:
        """Execute a keyword search and return the summary payload."""
        ...


@dataclass(slots=True)
class InstagramMemoryStore:
    """Manage durable state files used by the Instagram discovery harness."""

    memory_path: Path

    def __post_init__(self) -> None:
        self.memory_path = Path(self.memory_path)

    @property
    def icp_profiles_path(self) -> Path:
        return self.memory_path / ICP_PROFILES_FILENAME

    @property
    def search_history_path(self) -> Path:
        return self.memory_path / SEARCH_HISTORY_FILENAME

    @property
    def lead_database_path(self) -> Path:
        return self.memory_path / LEAD_DATABASE_FILENAME

    @property
    def runtime_parameters_path(self) -> Path:
        return self.memory_path / RUNTIME_PARAMETERS_FILENAME

    @property
    def agent_identity_path(self) -> Path:
        return self.memory_path / AGENT_IDENTITY_FILENAME

    @property
    def additional_prompt_path(self) -> Path:
        return self.memory_path / ADDITIONAL_PROMPT_FILENAME

    def prepare(self) -> None:
        self.memory_path.mkdir(parents=True, exist_ok=True)
        _ensure_json_file(self.icp_profiles_path, [])
        _ensure_json_file(self.search_history_path, [])
        _ensure_json_file(self.lead_database_path, InstagramLeadDatabase().as_dict())
        _ensure_json_file(self.runtime_parameters_path, {})
        _ensure_text_file(self.agent_identity_path, DEFAULT_AGENT_IDENTITY)
        _ensure_text_file(self.additional_prompt_path, "")

    def read_icp_profiles(self) -> list[str]:
        payload = _read_json_file(self.icp_profiles_path, expected_type=list)
        return [str(value).strip() for value in payload if str(value).strip()]

    def write_icp_profiles(self, profiles: Sequence[str]) -> None:
        cleaned = [value.strip() for value in profiles if value and value.strip()]
        _write_json(self.icp_profiles_path, cleaned)

    def read_search_history(self) -> list[InstagramSearchRecord]:
        payload = _read_json_file(self.search_history_path, expected_type=list)
        return [InstagramSearchRecord.from_dict(item) for item in payload]

    def read_recent_searches(self, limit: int) -> list[InstagramSearchRecord]:
        return self.read_search_history()[-limit:]

    def append_search(self, record: InstagramSearchRecord) -> None:
        history = self.read_search_history()
        history.append(record)
        _write_json(self.search_history_path, [item.as_dict() for item in history])

    def has_searched(self, keyword: str) -> bool:
        normalized_keyword = keyword.strip().lower()
        if not normalized_keyword:
            return False
        return any(record.keyword.lower() == normalized_keyword for record in self.read_search_history())

    def read_lead_database(self) -> InstagramLeadDatabase:
        payload = _read_json_file(self.lead_database_path, expected_type=dict)
        return InstagramLeadDatabase.from_dict(payload)

    def read_recent_leads(self, limit: int) -> list[InstagramLeadRecord]:
        database = self.read_lead_database()
        return list(database.leads[-limit:])

    def merge_leads(self, leads: Sequence[InstagramLeadRecord]) -> LeadMergeSummary:
        database = self.read_lead_database()
        lead_index = {lead.source_url: lead for lead in database.leads}
        email_set = {email.lower() for email in database.emails}

        new_leads = 0
        updated_leads = 0
        new_emails = 0

        for lead in leads:
            existing = lead_index.get(lead.source_url)
            if existing is None:
                lead_index[lead.source_url] = lead
                new_leads += 1
            else:
                merged_record = InstagramLeadRecord(
                    source_url=existing.source_url,
                    source_keyword=existing.source_keyword or lead.source_keyword,
                    found_at=existing.found_at,
                    emails=tuple(_dedupe_emails((*existing.emails, *lead.emails))),
                    title=existing.title or lead.title,
                    snippet=existing.snippet or lead.snippet,
                )
                if merged_record != existing:
                    lead_index[lead.source_url] = merged_record
                    updated_leads += 1

            for email in lead.emails:
                normalized_email = email.lower()
                if normalized_email not in email_set:
                    email_set.add(normalized_email)
                    new_emails += 1

        persisted_emails = tuple(sorted(email_set))
        persisted_leads = tuple(sorted(lead_index.values(), key=lambda item: (item.found_at, item.source_url)))
        _write_json(
            self.lead_database_path,
            InstagramLeadDatabase(leads=persisted_leads, emails=persisted_emails).as_dict(),
        )
        return LeadMergeSummary(
            new_emails=new_emails,
            new_leads=new_leads,
            total_emails=len(persisted_emails),
            total_leads=len(persisted_leads),
            updated_leads=updated_leads,
        )

    def get_emails(self) -> list[str]:
        return list(self.read_lead_database().emails)

    def get_leads(self) -> list[InstagramLeadRecord]:
        return list(self.read_lead_database().leads)

    def read_runtime_parameters(self) -> dict[str, Any]:
        return _read_json_file(self.runtime_parameters_path, expected_type=dict)

    def write_runtime_parameters(self, parameters: dict[str, Any]) -> None:
        _write_json(self.runtime_parameters_path, parameters)

    def read_agent_identity(self) -> str:
        return self.agent_identity_path.read_text(encoding="utf-8").strip()

    def write_agent_identity(self, text: str) -> None:
        _write_text(self.agent_identity_path, text)

    def read_additional_prompt(self) -> str:
        return self.additional_prompt_path.read_text(encoding="utf-8").strip()

    def write_additional_prompt(self, text: str) -> None:
        _write_text(self.additional_prompt_path, text)


def build_instagram_google_query(keyword: str) -> str:
    """Build the canonical Google search query for one keyword."""
    cleaned_keyword = keyword.strip()
    if not cleaned_keyword:
        raise ValueError("keyword must not be blank.")
    return f'site:instagram .com "@gmail .com" {cleaned_keyword}'


def build_instagram_google_fallback_query(keyword: str) -> str:
    """Build the Google fallback query when the spaced query yields no results."""
    cleaned_keyword = keyword.strip()
    if not cleaned_keyword:
        raise ValueError("keyword must not be blank.")
    return f'site:instagram.com "@gmail.com" {cleaned_keyword}'


def extract_emails(text: str) -> list[str]:
    """Return unique normalized email addresses from a text blob."""
    if not text:
        return []
    return _dedupe_emails(_normalize_email_match(match.group(0)) for match in _EMAIL_PATTERN.finditer(text))


def normalize_instagram_runtime_parameters(parameters: dict[str, Any]) -> dict[str, Any]:
    """Validate and type-coerce runtime parameters for the Instagram agent."""
    return INSTAGRAM_HARNESS_MANIFEST.coerce_runtime_parameters(parameters)


INSTAGRAM_HARNESS_MANIFEST = HarnessManifest(
    manifest_id="instagram",
    agent_name="instagram_keyword_discovery",
    display_name="Instagram Keyword Discovery",
    module_path="harnessiq.agents.instagram",
    class_name="InstagramKeywordDiscoveryAgent",
    cli_command="instagram",
    cli_adapter_path="harnessiq.cli.adapters.instagram:InstagramHarnessCliAdapter",
    default_memory_root="memory/instagram",
    prompt_path="harnessiq/agents/instagram/prompts/master_prompt.md",
    runtime_parameters=(
        HarnessParameterSpec("max_tokens", "integer", "Maximum model context budget for the harness.", default=DEFAULT_AGENT_MAX_TOKENS),
        HarnessParameterSpec("recent_result_window", "integer", "Number of recent leads kept in prompt context.", default=DEFAULT_RECENT_RESULT_WINDOW),
        HarnessParameterSpec("recent_search_window", "integer", "Number of recent searches kept in prompt context.", default=DEFAULT_RECENT_SEARCH_WINDOW),
        HarnessParameterSpec("reset_threshold", "number", "Fraction of max_tokens that triggers a reset.", default=DEFAULT_AGENT_RESET_THRESHOLD),
        HarnessParameterSpec("search_result_limit", "integer", "Maximum results requested from the search backend.", default=DEFAULT_SEARCH_RESULT_LIMIT),
    ),
    memory_files=(
        HarnessMemoryFileSpec("icp_profiles", ICP_PROFILES_FILENAME, "Persisted ICP descriptions.", format="json"),
        HarnessMemoryFileSpec("search_history", SEARCH_HISTORY_FILENAME, "Durable Instagram search history.", format="json"),
        HarnessMemoryFileSpec("lead_database", LEAD_DATABASE_FILENAME, "Persisted deduplicated leads and emails.", format="json"),
        HarnessMemoryFileSpec("runtime_parameters", RUNTIME_PARAMETERS_FILENAME, "Persisted typed runtime overrides.", format="json"),
        HarnessMemoryFileSpec("agent_identity", AGENT_IDENTITY_FILENAME, "Override for the Instagram system identity.", format="text"),
        HarnessMemoryFileSpec("additional_prompt", ADDITIONAL_PROMPT_FILENAME, "Additional free-form prompt data.", format="text"),
    ),
    provider_families=("playwright",),
    output_schema={
        "type": "object",
        "properties": {
            "emails": {"type": "array", "items": {"type": "string"}},
            "leads": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
            "search_history": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
        },
        "additionalProperties": False,
    },
)


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
        _write_text(path, default_content)


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


def _dedupe_emails(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip().strip(".,;:!?()[]{}<>\"'").lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _dedupe_strings(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _normalize_email_match(value: str) -> str:
    return re.sub(r"\s+", "", value.strip()).lower()


__all__ = [
    "ADDITIONAL_PROMPT_FILENAME",
    "AGENT_IDENTITY_FILENAME",
    "DEFAULT_AGENT_IDENTITY",
    "DEFAULT_INSTAGRAM_BROWSER_CHANNEL",
    "DEFAULT_INSTAGRAM_BROWSER_INIT_SCRIPT",
    "DEFAULT_INSTAGRAM_BROWSER_LAUNCH_ARGS",
    "DEFAULT_INSTAGRAM_BROWSER_VIEWPORT",
    "DEFAULT_INSTAGRAM_HEADLESS",
    "DEFAULT_INSTAGRAM_NETWORK_IDLE_TIMEOUT_MS",
    "DEFAULT_INSTAGRAM_TIMEOUT_MS",
    "DEFAULT_RECENT_RESULT_WINDOW",
    "DEFAULT_RECENT_SEARCH_WINDOW",
    "DEFAULT_SEARCH_RESULT_LIMIT",
    "ICP_PROFILES_FILENAME",
    "INSTAGRAM_HARNESS_MANIFEST",
    "INSTAGRAM_GOOGLE_SEARCH_URL",
    "InstagramKeywordAgentConfig",
    "InstagramLeadDatabase",
    "InstagramLeadRecord",
    "InstagramMemoryStore",
    "InstagramSearchBackend",
    "InstagramSearchExecution",
    "InstagramSearchRecord",
    "LEAD_DATABASE_FILENAME",
    "LeadMergeSummary",
    "RUNTIME_PARAMETERS_FILENAME",
    "SEARCH_HISTORY_FILENAME",
    "build_instagram_google_fallback_query",
    "build_instagram_google_query",
    "extract_emails",
    "normalize_instagram_runtime_parameters",
]
