"""Shared configuration, manifest metadata, and memory helpers for Research Sweep."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from harnessiq.shared.agents import DEFAULT_AGENT_MAX_TOKENS
from harnessiq.shared.harness_manifest import HarnessManifest, HarnessMemoryFileSpec, HarnessParameterSpec

DEFAULT_RESEARCH_SWEEP_RESET_THRESHOLD = 0.85
QUERY_FILENAME = "query.txt"
ADDITIONAL_PROMPT_FILENAME = "additional_prompt.md"
RUNTIME_PARAMETERS_FILENAME = "runtime_parameters.json"
CUSTOM_PARAMETERS_FILENAME = "custom_parameters.json"
CONTEXT_RUNTIME_STATE_FILENAME = "context_runtime_state.json"
DEFAULT_ALLOWED_SERPER_OPERATIONS = ("search", "scholar")
RESEARCH_SWEEP_MEMORY_FIELD_RULES = {
    "query": "write_once",
    "sites_remaining": "overwrite",
    "continuation_pointer": "overwrite",
    "site_results": "append",
    "all_sites_empty": "overwrite",
    "final_report": "overwrite",
}
RESEARCH_SWEEP_MEMORY_FIELD_ORDER = (
    "query",
    "sites_remaining",
    "continuation_pointer",
    "site_results",
    "all_sites_empty",
    "final_report",
)


@dataclass(frozen=True, slots=True)
class ResearchSweepSite:
    """One canonical research source in the sweep order."""

    index: int
    site_key: str
    site_name: str
    host: str
    serper_operation: str
    scoped_query_prefix: str | None = None

    def build_query(self, query: str) -> str:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("Research query must not be blank.")
        if self.scoped_query_prefix is None:
            return normalized_query
        return f"{self.scoped_query_prefix} {normalized_query}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "site_key": self.site_key,
            "site_name": self.site_name,
            "url": self.host,
            "serper_operation": self.serper_operation,
            "scoped_query_prefix": self.scoped_query_prefix,
        }


CANONICAL_RESEARCH_SWEEP_SITES: tuple[ResearchSweepSite, ...] = (
    ResearchSweepSite(
        index=1,
        site_key="google_scholar",
        site_name="Google Scholar",
        host="scholar.google.com",
        serper_operation="scholar",
    ),
    ResearchSweepSite(
        index=2,
        site_key="pubmed",
        site_name="PubMed",
        host="pubmed.ncbi.nlm.nih.gov",
        serper_operation="search",
        scoped_query_prefix="site:pubmed.ncbi.nlm.nih.gov",
    ),
    ResearchSweepSite(
        index=3,
        site_key="arxiv",
        site_name="arXiv",
        host="arxiv.org",
        serper_operation="search",
        scoped_query_prefix="site:arxiv.org",
    ),
    ResearchSweepSite(
        index=4,
        site_key="ssrn",
        site_name="SSRN",
        host="ssrn.com",
        serper_operation="search",
        scoped_query_prefix="site:ssrn.com",
    ),
    ResearchSweepSite(
        index=5,
        site_key="doaj",
        site_name="DOAJ",
        host="doaj.org",
        serper_operation="search",
        scoped_query_prefix="site:doaj.org",
    ),
    ResearchSweepSite(
        index=6,
        site_key="semantic_scholar",
        site_name="Semantic Scholar",
        host="semanticscholar.org",
        serper_operation="search",
        scoped_query_prefix="site:semanticscholar.org",
    ),
    ResearchSweepSite(
        index=7,
        site_key="jstor",
        site_name="JSTOR",
        host="jstor.org",
        serper_operation="search",
        scoped_query_prefix="site:jstor.org",
    ),
    ResearchSweepSite(
        index=8,
        site_key="base",
        site_name="BASE",
        host="base-search.net",
        serper_operation="search",
        scoped_query_prefix="site:base-search.net",
    ),
    ResearchSweepSite(
        index=9,
        site_key="core",
        site_name="CORE",
        host="core.ac.uk",
        serper_operation="search",
        scoped_query_prefix="site:core.ac.uk",
    ),
)
CANONICAL_SITE_KEYS = tuple(site.site_key for site in CANONICAL_RESEARCH_SWEEP_SITES)
CANONICAL_SITE_INDEX = {site.site_key: site for site in CANONICAL_RESEARCH_SWEEP_SITES}


@dataclass(frozen=True, slots=True)
class ResearchSweepAgentConfig:
    """Runtime and configuration inputs for one ResearchSweepAgent instance."""

    memory_path: Path
    query: str
    allowed_serper_operations: tuple[str, ...] = DEFAULT_ALLOWED_SERPER_OPERATIONS
    additional_prompt: str = ""
    max_tokens: int = DEFAULT_AGENT_MAX_TOKENS
    reset_threshold: float = DEFAULT_RESEARCH_SWEEP_RESET_THRESHOLD

    def __post_init__(self) -> None:
        normalized_query = self.query.strip()
        if not normalized_query:
            raise ValueError("query must not be blank.")
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be greater than zero.")
        if not 0 < self.reset_threshold <= 1:
            raise ValueError("reset_threshold must be between 0 and 1.")
        object.__setattr__(self, "memory_path", Path(self.memory_path))
        object.__setattr__(self, "query", normalized_query)
        object.__setattr__(
            self,
            "allowed_serper_operations",
            normalize_allowed_serper_operations(self.allowed_serper_operations),
        )
        object.__setattr__(self, "additional_prompt", self.additional_prompt.strip())


@dataclass(slots=True)
class ResearchSweepMemoryStore:
    """File-backed config and inspection helpers for the research sweep harness."""

    memory_path: Path

    def __post_init__(self) -> None:
        self.memory_path = Path(self.memory_path)

    @property
    def query_path(self) -> Path:
        return self.memory_path / QUERY_FILENAME

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
    def context_runtime_state_path(self) -> Path:
        return self.memory_path / CONTEXT_RUNTIME_STATE_FILENAME

    def prepare(self) -> None:
        self.memory_path.mkdir(parents=True, exist_ok=True)
        _ensure_text_file(self.query_path, "")
        _ensure_text_file(self.additional_prompt_path, "")
        _ensure_json_file(self.runtime_parameters_path, {})
        _ensure_json_file(
            self.custom_parameters_path,
            {"allowed_serper_operations": ",".join(DEFAULT_ALLOWED_SERPER_OPERATIONS)},
        )

    def read_query(self) -> str:
        return self.query_path.read_text(encoding="utf-8").strip()

    def write_query(self, query: str) -> Path:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("Research sweep query must not be blank.")
        return _write_text(self.query_path, normalized_query)

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

    def read_context_runtime_state(self) -> dict[str, Any]:
        return _read_json_file(self.context_runtime_state_path, expected_type=dict)

    def clear_context_runtime_state(self) -> None:
        if self.context_runtime_state_path.exists():
            self.context_runtime_state_path.unlink()

    def read_research_memory(self) -> dict[str, Any]:
        state = self.read_context_runtime_state()
        raw_memory_fields = state.get("memory_fields", {})
        if not isinstance(raw_memory_fields, dict):
            return {}
        return {
            field_name: deepcopy(raw_memory_fields[field_name])
            for field_name in RESEARCH_SWEEP_MEMORY_FIELD_ORDER
            if field_name in raw_memory_fields
        }

    def read_research_memory_summary(self) -> dict[str, Any]:
        memory = self.read_research_memory()
        site_results = memory.get("site_results", [])
        sites_remaining = memory.get("sites_remaining", [])
        return {
            "all_sites_empty": memory.get("all_sites_empty"),
            "completed_sites": len(site_results) if isinstance(site_results, list) else 0,
            "continuation_pointer": memory.get("continuation_pointer"),
            "final_report_present": bool(memory.get("final_report")),
            "site_result_count": len(site_results) if isinstance(site_results, list) else 0,
            "sites_remaining": sites_remaining if isinstance(sites_remaining, list) else [],
        }

    def read_final_report(self) -> str | None:
        final_report = self.read_research_memory().get("final_report")
        if isinstance(final_report, str) and final_report.strip():
            return final_report
        return None


def normalize_allowed_serper_operations(value: str | Sequence[str] | None) -> tuple[str, ...]:
    """Normalize the allowed-operation configuration to the required search/scholar pair."""
    if value is None:
        operations = list(DEFAULT_ALLOWED_SERPER_OPERATIONS)
    elif isinstance(value, str):
        operations = [item.strip() for item in value.split(",") if item.strip()]
    else:
        operations = [str(item).strip() for item in value if str(item).strip()]

    if set(operations) != set(DEFAULT_ALLOWED_SERPER_OPERATIONS):
        rendered = ", ".join(DEFAULT_ALLOWED_SERPER_OPERATIONS)
        raise ValueError(
            "allowed_serper_operations must resolve to exactly 'search' and 'scholar'. "
            f"Expected: {rendered}."
        )
    return tuple(
        operation for operation in DEFAULT_ALLOWED_SERPER_OPERATIONS if operation in set(operations)
    )


def normalize_research_sweep_runtime_parameters(parameters: Mapping[str, Any]) -> dict[str, Any]:
    """Type-coerce manifest-declared runtime parameters for the research sweep harness."""
    return RESEARCH_SWEEP_HARNESS_MANIFEST.coerce_runtime_parameters(parameters)


def normalize_research_sweep_custom_parameters(parameters: Mapping[str, Any]) -> dict[str, Any]:
    """Type-coerce manifest-declared custom parameters for the research sweep harness."""
    payload = RESEARCH_SWEEP_HARNESS_MANIFEST.coerce_custom_parameters(parameters)
    if "allowed_serper_operations" in payload:
        payload["allowed_serper_operations"] = ",".join(
            normalize_allowed_serper_operations(payload["allowed_serper_operations"])
        )
    return payload


def validate_query_for_run(query: str) -> str:
    """Return a stripped query or raise a CLI-friendly error when it is missing."""
    normalized = query.strip()
    if not normalized:
        raise ValueError(
            "Research sweep run requires a configured query. "
            "Run `harnessiq research-sweep configure --query-text ...` first."
        )
    return normalized


def build_research_sweep_configuration_payload(
    *,
    query: str,
    allowed_serper_operations: Sequence[str],
    search_date: str,
) -> dict[str, Any]:
    """Build the static configuration payload injected into the context window."""
    return {
        "allowed_serper_operations": list(normalize_allowed_serper_operations(allowed_serper_operations)),
        "canonical_site_order": [site.as_dict() for site in CANONICAL_RESEARCH_SWEEP_SITES],
        "query": validate_query_for_run(query),
        "search_date": search_date,
    }


RESEARCH_SWEEP_HARNESS_MANIFEST = HarnessManifest(
    manifest_id="research_sweep",
    agent_name="research_sweep_agent",
    display_name="Research Sweep",
    module_path="harnessiq.agents.research_sweep",
    class_name="ResearchSweepAgent",
    cli_command="research-sweep",
    cli_adapter_path="harnessiq.cli.adapters.research_sweep:ResearchSweepHarnessCliAdapter",
    default_memory_root="memory/research_sweep",
    prompt_path="harnessiq/agents/research_sweep/prompts/master_prompt.md",
    runtime_parameters=(
        HarnessParameterSpec(
            "max_tokens",
            "integer",
            "Maximum model context budget for the research sweep harness.",
            default=DEFAULT_AGENT_MAX_TOKENS,
        ),
        HarnessParameterSpec(
            "reset_threshold",
            "number",
            "Fraction of max_tokens that triggers an automatic transcript reset.",
            default=DEFAULT_RESEARCH_SWEEP_RESET_THRESHOLD,
        ),
    ),
    custom_parameters=(
        HarnessParameterSpec(
            "query",
            "string",
            "Research query executed across the canonical nine-site sweep.",
        ),
        HarnessParameterSpec(
            "allowed_serper_operations",
            "string",
            "Comma-delimited Serper operations allowed for this harness. Must resolve to search,scholar.",
            default="search,scholar",
        ),
    ),
    memory_files=(
        HarnessMemoryFileSpec(
            "query",
            QUERY_FILENAME,
            "Configured research query used to seed the sweep.",
            format="text",
        ),
        HarnessMemoryFileSpec(
            "additional_prompt",
            ADDITIONAL_PROMPT_FILENAME,
            "Optional free-form prompt text appended to the static master prompt.",
            format="markdown",
        ),
        HarnessMemoryFileSpec(
            "runtime_parameters",
            RUNTIME_PARAMETERS_FILENAME,
            "Persisted typed runtime overrides for the research sweep harness.",
            format="json",
        ),
        HarnessMemoryFileSpec(
            "custom_parameters",
            CUSTOM_PARAMETERS_FILENAME,
            "Persisted typed custom parameters for the research sweep harness.",
            format="json",
        ),
        HarnessMemoryFileSpec(
            "context_runtime_state",
            CONTEXT_RUNTIME_STATE_FILENAME,
            "Durable context runtime state backing the Research Sweep Memory schema and final report.",
            format="json",
        ),
    ),
    provider_families=("serper",),
    output_schema={
        "type": "object",
        "properties": {
            "all_sites_empty": {"type": ["boolean", "null"]},
            "continuation_pointer": {"type": ["string", "null"]},
            "final_report": {"type": ["string", "null"]},
            "query": {"type": "string"},
            "site_results": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
        },
        "additionalProperties": False,
    },
)


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


__all__ = [
    "ADDITIONAL_PROMPT_FILENAME",
    "CANONICAL_RESEARCH_SWEEP_SITES",
    "CANONICAL_SITE_INDEX",
    "CANONICAL_SITE_KEYS",
    "CONTEXT_RUNTIME_STATE_FILENAME",
    "CUSTOM_PARAMETERS_FILENAME",
    "DEFAULT_ALLOWED_SERPER_OPERATIONS",
    "DEFAULT_RESEARCH_SWEEP_RESET_THRESHOLD",
    "QUERY_FILENAME",
    "RESEARCH_SWEEP_HARNESS_MANIFEST",
    "RESEARCH_SWEEP_MEMORY_FIELD_ORDER",
    "RESEARCH_SWEEP_MEMORY_FIELD_RULES",
    "RUNTIME_PARAMETERS_FILENAME",
    "ResearchSweepAgentConfig",
    "ResearchSweepMemoryStore",
    "ResearchSweepSite",
    "build_research_sweep_configuration_payload",
    "normalize_allowed_serper_operations",
    "normalize_research_sweep_custom_parameters",
    "normalize_research_sweep_runtime_parameters",
    "validate_query_for_run",
]
