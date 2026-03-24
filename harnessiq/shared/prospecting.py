"""Shared data models, defaults, and durable memory for Google Maps prospecting."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from harnessiq.shared.agents import DEFAULT_AGENT_MAX_TOKENS, DEFAULT_AGENT_RESET_THRESHOLD
from harnessiq.shared.harness_manifest import HarnessManifest, HarnessMemoryFileSpec, HarnessParameterSpec

COMPANY_DESCRIPTION_FILENAME = "company_description.md"
AGENT_IDENTITY_FILENAME = "agent_identity.md"
ADDITIONAL_PROMPT_FILENAME = "additional_prompt.md"
RUNTIME_PARAMETERS_FILENAME = "runtime_parameters.json"
CUSTOM_PARAMETERS_FILENAME = "custom_parameters.json"
STATE_FILENAME = "prospecting_state.json"
QUALIFIED_LEADS_FILENAME = "qualified_leads.jsonl"
BROWSER_DATA_DIRNAME = "browser-data"

DEFAULT_AGENT_IDENTITY = (
    "A disciplined Google Maps prospecting agent that turns a target company description into "
    "iterative Maps searches, evaluates each business deterministically, and preserves durable "
    "state so search progress and qualified leads survive context resets."
)
DEFAULT_COMPANY_DESCRIPTION = "Describe the companies you want targeted on Google Maps."
DEFAULT_QUALIFICATION_THRESHOLD = 9
DEFAULT_SUMMARIZE_AT_X = 10
DEFAULT_MAX_SEARCHES_PER_RUN = 50
DEFAULT_MAX_LISTINGS_PER_SEARCH = 10
DEFAULT_WEBSITE_INSPECT_ENABLED = True
DEFAULT_SINK_RECORD_TYPE = "prospecting_lead"
DEFAULT_GOOGLE_MAPS_SEARCH_BASE_URL = "https://www.google.com/maps/search/"
RUN_STATUS_IN_PROGRESS = "in_progress"
RUN_STATUS_CONSOLIDATING = "consolidating"
RUN_STATUS_COMPLETE = "complete"
RUN_STATUS_ERROR = "error"

DEFAULT_EVAL_SYSTEM_PROMPT = """You are a lead qualification engine for an AI website-visibility service. You evaluate
whether a business listing is a strong sales prospect.

You will receive:
1. A natural language description of the target company profile
2. Extracted data from a Google Maps business listing

Your task is to evaluate the listing against the target profile and return ONLY a JSON
object with no other text.

Qualification threshold: score >= 9 out of 15.

HARD DISQUALIFIERS (return DISQUALIFIED immediately, score = 0):
- No website linked on the listing
- National or regional chain (franchise indicator present)
- Permanently closed or temporarily closed
- Fewer than 2 reviews total

SCORING RUBRIC (1-3 per factor):

Factor 1 - Competitive Pressure
  1 = 0-2 competitors ranked above them in Maps search
  2 = 3-5 competitors above them
  3 = 6+ above / buried on page 2+

Factor 2 - Review Gap vs. Top Competitor
  1 = gap < 20 reviews
  2 = gap 20-100 reviews
  3 = gap > 100 reviews

Factor 3 - Profile Activity (count: responds to reviews, recent review < 90 days,
  Google Posts present, Q&A answered, photos beyond street view, description present)
  1 = 0-2 signals
  2 = 3-4 signals
  3 = 5-6 signals

Factor 4 - Website Quality
  1 = modern, fast, apparent SEO work
  2 = functional but dated, no blog, no recent content
  3 = poor - slow, mobile-unfriendly, placeholder, or Facebook as website

Factor 5 - Industry Margin Tier
  1 = low-margin (restaurants, salons, gyms, cleaners)
  2 = mid-margin (auto repair, real estate, contractors, fitness studios)
  3 = high-margin (dentists, attorneys, chiropractors, HVAC, med spas, funeral homes)

PITCH HOOK: If QUALIFIED, write a 1-2 sentence pitch hook anchored in specific data.

Return ONLY valid JSON matching the output contract. No other text."""

SEARCH_SUMMARY_SYSTEM_PROMPT = """You summarize completed Google Maps searches for a prospecting run.
Return ONLY JSON with the schema {"summary": "<compact summary>", "insights": ["..."]}.
Keep the summary compact, mention industries and locations already searched, and highlight patterns that should steer future search expansion."""

NEXT_QUERY_SYSTEM_PROMPT = """You generate the next Google Maps search pair for a prospecting run.
Rules:
- Stay anchored to the company description.
- Never repeat an already-searched (query, location) pair.
- Diversify geography before repeating the exact same city.
- Return ONLY JSON with the schema {"query": "...", "location": "..."}.
- If no sensible next search remains, return {"query": "", "location": ""}."""


@dataclass(frozen=True, slots=True)
class ProspectingAgentConfig:
    """Runtime and custom configuration for the prospecting harness."""

    memory_path: Path
    max_tokens: int = DEFAULT_AGENT_MAX_TOKENS
    reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD
    qualification_threshold: int = DEFAULT_QUALIFICATION_THRESHOLD
    summarize_at_x: int = DEFAULT_SUMMARIZE_AT_X
    max_searches_per_run: int = DEFAULT_MAX_SEARCHES_PER_RUN
    max_listings_per_search: int = DEFAULT_MAX_LISTINGS_PER_SEARCH
    website_inspect_enabled: bool = DEFAULT_WEBSITE_INSPECT_ENABLED
    sink_record_type: str = DEFAULT_SINK_RECORD_TYPE
    eval_system_prompt: str = DEFAULT_EVAL_SYSTEM_PROMPT

    def __post_init__(self) -> None:
        object.__setattr__(self, "memory_path", Path(self.memory_path))
        if self.qualification_threshold <= 0:
            raise ValueError("qualification_threshold must be positive.")
        if self.summarize_at_x <= 0:
            raise ValueError("summarize_at_x must be positive.")
        if self.max_searches_per_run <= 0:
            raise ValueError("max_searches_per_run must be positive.")
        if self.max_listings_per_search <= 0:
            raise ValueError("max_listings_per_search must be positive.")
        if not self.sink_record_type.strip():
            raise ValueError("sink_record_type must not be blank.")
        if not self.eval_system_prompt.strip():
            raise ValueError("eval_system_prompt must not be blank.")


@dataclass(frozen=True, slots=True)
class SearchRecord:
    """Summary of one completed Google Maps search."""

    index: int
    query: str
    location: str
    listings_found: int
    listings_evaluated: int
    qualified_count: int
    completed_at: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SearchRecord":
        return cls(
            index=int(payload["index"]),
            query=str(payload["query"]),
            location=str(payload["location"]),
            listings_found=int(payload["listings_found"]),
            listings_evaluated=int(payload["listings_evaluated"]),
            qualified_count=int(payload["qualified_count"]),
            completed_at=str(payload["completed_at"]),
        )


@dataclass(frozen=True, slots=True)
class CurrentSearchProgress:
    """Active search pointer used for mid-search resume."""

    index: int
    query: str
    location: str
    last_listing_position: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CurrentSearchProgress":
        return cls(
            index=int(payload["index"]),
            query=str(payload["query"]),
            location=str(payload["location"]),
            last_listing_position=int(payload["last_listing_position"]),
        )


@dataclass(frozen=True, slots=True)
class QualifiedLeadRecord:
    """Sink-friendly qualified lead record persisted by the prospecting agent."""

    record_type: str
    run_id: str
    business_name: str
    maps_url: str
    website_url: str | None
    score: int
    verdict: str
    score_breakdown: dict[str, Any]
    pitch_hook: str | None
    search_query: str
    search_index: int
    evaluated_at: str
    raw_listing: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "record_type": self.record_type,
            "run_id": self.run_id,
            "business_name": self.business_name,
            "maps_url": self.maps_url,
            "website_url": self.website_url,
            "score": self.score,
            "verdict": self.verdict,
            "score_breakdown": dict(self.score_breakdown),
            "pitch_hook": self.pitch_hook,
            "search_query": self.search_query,
            "search_index": self.search_index,
            "evaluated_at": self.evaluated_at,
            "raw_listing": dict(self.raw_listing),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "QualifiedLeadRecord":
        return cls(
            record_type=str(payload["record_type"]),
            run_id=str(payload["run_id"]),
            business_name=str(payload["business_name"]),
            maps_url=str(payload["maps_url"]),
            website_url=str(payload["website_url"]) if payload.get("website_url") is not None else None,
            score=int(payload["score"]),
            verdict=str(payload["verdict"]),
            score_breakdown=dict(payload.get("score_breakdown", {})),
            pitch_hook=str(payload["pitch_hook"]) if payload.get("pitch_hook") is not None else None,
            search_query=str(payload["search_query"]),
            search_index=int(payload["search_index"]),
            evaluated_at=str(payload["evaluated_at"]),
            raw_listing=dict(payload.get("raw_listing", {})),
        )


@dataclass(frozen=True, slots=True)
class ProspectingState:
    """Durable search-progress state persisted between resets and runs."""

    run_id: str
    company_description: str
    searches_completed: tuple[SearchRecord, ...] = ()
    searches_summarized_through: int = 0
    search_history_summary: str | None = None
    last_completed_search_index: int = -1
    current_search_in_progress: CurrentSearchProgress | None = None
    qualified_leads_posted: int = 0
    disqualified_leads_count: int = 0
    session_reset_count: int = 0
    run_status: str = RUN_STATUS_IN_PROGRESS
    error_log: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "company_description": self.company_description,
            "searches_completed": [record.as_dict() for record in self.searches_completed],
            "searches_summarized_through": self.searches_summarized_through,
            "search_history_summary": self.search_history_summary,
            "last_completed_search_index": self.last_completed_search_index,
            "current_search_in_progress": (
                self.current_search_in_progress.as_dict() if self.current_search_in_progress is not None else None
            ),
            "qualified_leads_posted": self.qualified_leads_posted,
            "disqualified_leads_count": self.disqualified_leads_count,
            "session_reset_count": self.session_reset_count,
            "run_status": self.run_status,
            "error_log": list(self.error_log),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProspectingState":
        progress = payload.get("current_search_in_progress")
        return cls(
            run_id=str(payload["run_id"]),
            company_description=str(payload.get("company_description", "")),
            searches_completed=tuple(
                SearchRecord.from_dict(item) for item in payload.get("searches_completed", ())
            ),
            searches_summarized_through=int(payload.get("searches_summarized_through", 0)),
            search_history_summary=(
                str(payload["search_history_summary"])
                if payload.get("search_history_summary") is not None
                else None
            ),
            last_completed_search_index=int(payload.get("last_completed_search_index", -1)),
            current_search_in_progress=(
                CurrentSearchProgress.from_dict(progress) if isinstance(progress, Mapping) else None
            ),
            qualified_leads_posted=int(payload.get("qualified_leads_posted", 0)),
            disqualified_leads_count=int(payload.get("disqualified_leads_count", 0)),
            session_reset_count=int(payload.get("session_reset_count", 0)),
            run_status=str(payload.get("run_status", RUN_STATUS_IN_PROGRESS)),
            error_log=tuple(str(item) for item in payload.get("error_log", ())),
        )


@dataclass(slots=True)
class ProspectingMemoryStore:
    """Manage durable state files used by the prospecting harness."""

    memory_path: Path

    def __post_init__(self) -> None:
        self.memory_path = Path(self.memory_path)

    @property
    def company_description_path(self) -> Path:
        return self.memory_path / COMPANY_DESCRIPTION_FILENAME

    @property
    def agent_identity_path(self) -> Path:
        return self.memory_path / AGENT_IDENTITY_FILENAME

    @property
    def additional_prompt_path(self) -> Path:
        return self.memory_path / ADDITIONAL_PROMPT_FILENAME

    @property
    def runtime_parameters_path(self) -> Path:
        return self.memory_path / RUNTIME_PARAMETERS_FILENAME

    @property
    def custom_parameters_path(self) -> Path:
        return self.memory_path / CUSTOM_PARAMETERS_FILENAME

    @property
    def state_path(self) -> Path:
        return self.memory_path / STATE_FILENAME

    @property
    def qualified_leads_path(self) -> Path:
        return self.memory_path / QUALIFIED_LEADS_FILENAME

    @property
    def browser_data_dir(self) -> Path:
        return self.memory_path / BROWSER_DATA_DIRNAME

    def prepare(self) -> None:
        self.memory_path.mkdir(parents=True, exist_ok=True)
        self.browser_data_dir.mkdir(parents=True, exist_ok=True)
        _ensure_text_file(self.company_description_path, DEFAULT_COMPANY_DESCRIPTION)
        _ensure_text_file(self.agent_identity_path, DEFAULT_AGENT_IDENTITY)
        _ensure_text_file(self.additional_prompt_path, "")
        _ensure_json_file(self.runtime_parameters_path, {})
        _ensure_json_file(self.custom_parameters_path, {})
        if not self.state_path.exists():
            self.write_state(
                ProspectingState(
                    run_id=new_run_id(),
                    company_description=self.read_company_description(),
                )
            )
        _ensure_text_file(self.qualified_leads_path, "")

    def read_company_description(self) -> str:
        return self.company_description_path.read_text(encoding="utf-8").strip()

    def write_company_description(self, content: str) -> Path:
        return _write_text(self.company_description_path, content)

    def read_agent_identity(self) -> str:
        return self.agent_identity_path.read_text(encoding="utf-8").strip()

    def write_agent_identity(self, content: str) -> Path:
        return _write_text(self.agent_identity_path, content)

    def read_additional_prompt(self) -> str:
        return self.additional_prompt_path.read_text(encoding="utf-8").strip()

    def write_additional_prompt(self, content: str) -> Path:
        return _write_text(self.additional_prompt_path, content)

    def read_runtime_parameters(self) -> dict[str, Any]:
        return _read_json_file(self.runtime_parameters_path, expected_type=dict)

    def write_runtime_parameters(self, parameters: Mapping[str, Any]) -> Path:
        return _write_json(self.runtime_parameters_path, dict(parameters))

    def read_custom_parameters(self) -> dict[str, Any]:
        return _read_json_file(self.custom_parameters_path, expected_type=dict)

    def write_custom_parameters(self, parameters: Mapping[str, Any]) -> Path:
        return _write_json(self.custom_parameters_path, dict(parameters))

    def read_state(self) -> ProspectingState:
        payload = _read_json_file(self.state_path, expected_type=dict)
        if not payload:
            return ProspectingState(run_id=new_run_id(), company_description=self.read_company_description())
        return ProspectingState.from_dict(payload)

    def write_state(self, state: ProspectingState) -> Path:
        return _write_json(self.state_path, state.as_dict())

    def update_state(self, **updates: Any) -> ProspectingState:
        current = self.read_state()
        data = current.as_dict()
        data.update(updates)
        next_state = ProspectingState.from_dict(data)
        self.write_state(next_state)
        return next_state

    def append_error(self, message: str) -> ProspectingState:
        state = self.read_state()
        return self.update_state(error_log=[*state.error_log, message])

    def append_qualified_lead(self, record: QualifiedLeadRecord) -> QualifiedLeadRecord:
        with self.qualified_leads_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.as_dict(), sort_keys=True))
            handle.write("\n")
        return record

    def read_qualified_leads(self) -> list[QualifiedLeadRecord]:
        if not self.qualified_leads_path.exists():
            return []
        records: list[QualifiedLeadRecord] = []
        for raw_line in self.qualified_leads_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                records.append(QualifiedLeadRecord.from_dict(payload))
        return records

    def qualified_count_for_search(self, search_index: int) -> int:
        return sum(1 for record in self.read_qualified_leads() if record.search_index == search_index)

    def ensure_state_matches_company_description(self) -> ProspectingState:
        state = self.read_state()
        company_description = self.read_company_description()
        if state.company_description == company_description:
            return state
        next_state = ProspectingState(
            run_id=new_run_id(),
            company_description=company_description,
        )
        self.write_state(next_state)
        self.qualified_leads_path.write_text("", encoding="utf-8")
        return next_state


PROSPECTING_HARNESS_MANIFEST = HarnessManifest(
    manifest_id="prospecting",
    agent_name="google_maps_prospecting",
    display_name="Google Maps Prospecting",
    module_path="harnessiq.agents.prospecting",
    class_name="GoogleMapsProspectingAgent",
    cli_command="prospecting",
    cli_adapter_path="harnessiq.cli.adapters.prospecting:ProspectingHarnessCliAdapter",
    default_memory_root="memory/prospecting",
    prompt_path="harnessiq/agents/prospecting/prompts/master_prompt.md",
    runtime_parameters=(
        HarnessParameterSpec("max_tokens", "integer", "Maximum model context budget for the harness.", default=DEFAULT_AGENT_MAX_TOKENS),
        HarnessParameterSpec("reset_threshold", "number", "Fraction of max_tokens that triggers a reset.", default=DEFAULT_AGENT_RESET_THRESHOLD),
    ),
    custom_parameters=(
        HarnessParameterSpec("qualification_threshold", "integer", "Minimum score required to qualify a lead.", default=DEFAULT_QUALIFICATION_THRESHOLD),
        HarnessParameterSpec("summarize_at_x", "integer", "Search count cadence for search-history summarization.", default=DEFAULT_SUMMARIZE_AT_X),
        HarnessParameterSpec("max_searches_per_run", "integer", "Maximum Google Maps searches per run.", default=DEFAULT_MAX_SEARCHES_PER_RUN),
        HarnessParameterSpec("max_listings_per_search", "integer", "Maximum listings evaluated per search.", default=DEFAULT_MAX_LISTINGS_PER_SEARCH),
        HarnessParameterSpec("website_inspect_enabled", "boolean", "Whether website inspection is enabled.", default=DEFAULT_WEBSITE_INSPECT_ENABLED),
        HarnessParameterSpec("sink_record_type", "string", "Record type emitted to output sinks.", default=DEFAULT_SINK_RECORD_TYPE),
        HarnessParameterSpec("eval_system_prompt", "string", "System prompt used for deterministic company evaluation.", default=DEFAULT_EVAL_SYSTEM_PROMPT),
    ),
    memory_files=(
        HarnessMemoryFileSpec("company_description", COMPANY_DESCRIPTION_FILENAME, "Durable company targeting description.", format="markdown"),
        HarnessMemoryFileSpec("agent_identity", AGENT_IDENTITY_FILENAME, "Override for the prospecting system identity.", format="markdown"),
        HarnessMemoryFileSpec("additional_prompt", ADDITIONAL_PROMPT_FILENAME, "Additional free-form prompt data.", format="markdown"),
        HarnessMemoryFileSpec("runtime_parameters", RUNTIME_PARAMETERS_FILENAME, "Persisted typed runtime overrides.", format="json"),
        HarnessMemoryFileSpec("custom_parameters", CUSTOM_PARAMETERS_FILENAME, "Persisted typed custom parameters.", format="json"),
        HarnessMemoryFileSpec("state", STATE_FILENAME, "Durable run state for search progress and resets.", format="json"),
        HarnessMemoryFileSpec("qualified_leads", QUALIFIED_LEADS_FILENAME, "Append-only qualified lead records.", format="jsonl"),
        HarnessMemoryFileSpec("browser_data", BROWSER_DATA_DIRNAME, "Persistent browser session directory.", kind="directory", format="directory"),
    ),
    provider_families=("playwright",),
    output_schema={
        "type": "object",
        "properties": {
            "company_description": {"type": "string"},
            "qualified_leads": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
            "searches_completed": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
            "summary": {"type": ["string", "null"]},
            "counts": {"type": "object", "additionalProperties": True},
        },
        "additionalProperties": False,
    },
)

SUPPORTED_PROSPECTING_RUNTIME_PARAMETERS = PROSPECTING_HARNESS_MANIFEST.runtime_parameter_names

SUPPORTED_PROSPECTING_CUSTOM_PARAMETERS = PROSPECTING_HARNESS_MANIFEST.custom_parameter_names


def normalize_prospecting_runtime_parameters(parameters: Mapping[str, Any]) -> dict[str, Any]:
    return PROSPECTING_HARNESS_MANIFEST.coerce_runtime_parameters(parameters)


def normalize_prospecting_custom_parameters(parameters: Mapping[str, Any]) -> dict[str, Any]:
    return PROSPECTING_HARNESS_MANIFEST.coerce_custom_parameters(parameters)


def is_placeholder_company_description(value: str) -> bool:
    normalized = value.strip()
    return not normalized or normalized == DEFAULT_COMPANY_DESCRIPTION


def validate_company_description_for_run(value: str) -> str:
    normalized = value.strip()
    if is_placeholder_company_description(normalized):
        raise ValueError(
            "Prospecting run requires a configured company description. "
            "Run `harnessiq prospecting configure --company-description-text ...` first."
        )
    return normalized


def new_run_id() -> str:
    return str(uuid4())


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def slugify_agent_name(agent_name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", agent_name.strip()).strip("-")
    if not cleaned:
        raise ValueError("Agent names must contain at least one alphanumeric character.")
    return cleaned


def _write_json(path: Path, payload: Any) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _write_text(path: Path, content: str) -> Path:
    rendered = content if not content or content.endswith("\n") else f"{content}\n"
    path.write_text(rendered, encoding="utf-8")
    return path


def _ensure_json_file(path: Path, default_payload: Any) -> None:
    if not path.exists():
        _write_json(path, default_payload)


def _ensure_text_file(path: Path, default_content: str) -> None:
    if not path.exists():
        _write_text(path, default_content)


def _read_json_file(path: Path, *, expected_type: type[dict] | type[list]) -> Any:
    if not path.exists():
        return expected_type()
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return expected_type()
    payload = json.loads(raw)
    if not isinstance(payload, expected_type):
        raise ValueError(f"Expected JSON {expected_type.__name__} in '{path.name}'.")
    return payload


def _coerce_int(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("Boolean values are not valid integer parameters.")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        return int(value)
    raise ValueError("Parameter must be an integer.")


def _coerce_float(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("Boolean values are not valid float parameters.")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        return float(value)
    raise ValueError("Parameter must be a float.")


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    raise ValueError("Parameter must be a boolean.")


def _coerce_string(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Parameter must be a non-empty string.")
    return value


__all__ = [
    "ADDITIONAL_PROMPT_FILENAME",
    "AGENT_IDENTITY_FILENAME",
    "BROWSER_DATA_DIRNAME",
    "COMPANY_DESCRIPTION_FILENAME",
    "CUSTOM_PARAMETERS_FILENAME",
    "CurrentSearchProgress",
    "DEFAULT_AGENT_IDENTITY",
    "DEFAULT_COMPANY_DESCRIPTION",
    "DEFAULT_EVAL_SYSTEM_PROMPT",
    "DEFAULT_GOOGLE_MAPS_SEARCH_BASE_URL",
    "DEFAULT_MAX_LISTINGS_PER_SEARCH",
    "DEFAULT_MAX_SEARCHES_PER_RUN",
    "DEFAULT_QUALIFICATION_THRESHOLD",
    "DEFAULT_SINK_RECORD_TYPE",
    "DEFAULT_SUMMARIZE_AT_X",
    "DEFAULT_WEBSITE_INSPECT_ENABLED",
    "NEXT_QUERY_SYSTEM_PROMPT",
    "ProspectingAgentConfig",
    "PROSPECTING_HARNESS_MANIFEST",
    "ProspectingMemoryStore",
    "ProspectingState",
    "QUALIFIED_LEADS_FILENAME",
    "QualifiedLeadRecord",
    "RUNTIME_PARAMETERS_FILENAME",
    "RUN_STATUS_COMPLETE",
    "RUN_STATUS_CONSOLIDATING",
    "RUN_STATUS_ERROR",
    "RUN_STATUS_IN_PROGRESS",
    "SEARCH_SUMMARY_SYSTEM_PROMPT",
    "SUPPORTED_PROSPECTING_CUSTOM_PARAMETERS",
    "SUPPORTED_PROSPECTING_RUNTIME_PARAMETERS",
    "STATE_FILENAME",
    "SearchRecord",
    "is_placeholder_company_description",
    "new_run_id",
    "normalize_prospecting_custom_parameters",
    "normalize_prospecting_runtime_parameters",
    "slugify_agent_name",
    "utcnow",
    "validate_company_description_for_run",
]
