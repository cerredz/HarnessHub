"""Shared contracts and durable memory store for the spawn-specialized-subagents harness."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from harnessiq.shared.agents import DEFAULT_AGENT_MAX_TOKENS
from harnessiq.shared.dtos.prompt_harnesses import SubAgentAssignmentDTO
from harnessiq.shared.harness_manifest import HarnessManifest, HarnessMemoryFileSpec, HarnessParameterSpec

DEFAULT_SPAWN_SUBAGENTS_RESET_THRESHOLD = 0.85
OBJECTIVE_FILENAME = "objective.md"
CURRENT_CONTEXT_FILENAME = "current_context.md"
ADDITIONAL_PROMPT_FILENAME = "additional_prompt.md"
PLAN_FILENAME = "plan.json"
WORKER_OUTPUTS_FILENAME = "worker_outputs.json"
INTEGRATION_SUMMARY_FILENAME = "integration_summary.json"
EXECUTION_LOG_FILENAME = "execution_log.jsonl"
README_FILENAME = "README.md"
RUNTIME_PARAMETERS_FILENAME = "runtime_parameters.json"
CUSTOM_PARAMETERS_FILENAME = "custom_parameters.json"
SPAWN_SPECIALIZED_SUBAGENTS_PROMPT_KEY = "spawn_specialized_subagents"


@dataclass(frozen=True, slots=True)
class SpawnSpecializedSubagentsConfig:
    """Runtime configuration for one delegation-orchestration harness instance."""

    memory_path: Path
    objective: str
    available_agent_types: tuple[str, ...] = ()
    current_context: str = ""
    additional_prompt: str = ""
    max_tokens: int = DEFAULT_AGENT_MAX_TOKENS
    reset_threshold: float = DEFAULT_SPAWN_SUBAGENTS_RESET_THRESHOLD

    def __post_init__(self) -> None:
        object.__setattr__(self, "memory_path", Path(self.memory_path))
        normalized_objective = self.objective.strip()
        if not normalized_objective:
            raise ValueError("objective must not be blank.")
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be greater than zero.")
        if not 0 < self.reset_threshold <= 1:
            raise ValueError("reset_threshold must be between 0 and 1.")
        object.__setattr__(self, "objective", normalized_objective)
        object.__setattr__(
            self,
            "available_agent_types",
            tuple(item.strip() for item in self.available_agent_types if str(item).strip()),
        )
        object.__setattr__(self, "current_context", self.current_context.strip())
        object.__setattr__(self, "additional_prompt", self.additional_prompt.strip())


@dataclass(slots=True)
class SpawnSpecializedSubagentsMemoryStore:
    """File-backed orchestration store for delegation planning and integration."""

    memory_path: Path

    def __post_init__(self) -> None:
        self.memory_path = Path(self.memory_path)

    @property
    def objective_path(self) -> Path:
        return self.memory_path / OBJECTIVE_FILENAME

    @property
    def current_context_path(self) -> Path:
        return self.memory_path / CURRENT_CONTEXT_FILENAME

    @property
    def additional_prompt_path(self) -> Path:
        return self.memory_path / ADDITIONAL_PROMPT_FILENAME

    @property
    def plan_path(self) -> Path:
        return self.memory_path / PLAN_FILENAME

    @property
    def worker_outputs_path(self) -> Path:
        return self.memory_path / WORKER_OUTPUTS_FILENAME

    @property
    def integration_summary_path(self) -> Path:
        return self.memory_path / INTEGRATION_SUMMARY_FILENAME

    @property
    def execution_log_path(self) -> Path:
        return self.memory_path / EXECUTION_LOG_FILENAME

    @property
    def readme_path(self) -> Path:
        return self.memory_path / README_FILENAME

    @property
    def runtime_parameters_path(self) -> Path:
        return self.memory_path / RUNTIME_PARAMETERS_FILENAME

    @property
    def custom_parameters_path(self) -> Path:
        return self.memory_path / CUSTOM_PARAMETERS_FILENAME

    def prepare(self) -> None:
        self.memory_path.mkdir(parents=True, exist_ok=True)
        _ensure_text_file(self.objective_path, "")
        _ensure_text_file(self.current_context_path, "")
        _ensure_text_file(self.additional_prompt_path, "")
        _ensure_json_file(
            self.plan_path,
            {
                "immediate_local_step": "",
                "assignments": [],
                "integration_criteria": [],
                "updated_at": "",
            },
        )
        _ensure_json_file(self.worker_outputs_path, [])
        _ensure_json_file(self.integration_summary_path, {})
        _ensure_text_file(self.execution_log_path, "")
        _ensure_text_file(self.readme_path, "")
        _ensure_json_file(self.runtime_parameters_path, {})
        _ensure_json_file(self.custom_parameters_path, {})

    def write_objective(self, objective: str) -> Path:
        normalized = objective.strip()
        if not normalized:
            raise ValueError("objective must not be blank.")
        return _write_text(self.objective_path, normalized)

    def read_objective(self) -> str:
        return _read_optional_text(self.objective_path)

    def write_current_context(self, content: str) -> Path:
        return _write_text(self.current_context_path, content)

    def read_current_context(self) -> str:
        return _read_optional_text(self.current_context_path)

    def write_additional_prompt(self, content: str) -> Path:
        return _write_text(self.additional_prompt_path, content)

    def read_additional_prompt(self) -> str:
        return _read_optional_text(self.additional_prompt_path)

    def write_runtime_parameters(self, parameters: Mapping[str, Any]) -> Path:
        return _write_json(self.runtime_parameters_path, dict(parameters))

    def read_runtime_parameters(self) -> dict[str, Any]:
        return _read_json_file(self.runtime_parameters_path, expected_type=dict)

    def write_custom_parameters(self, parameters: Mapping[str, Any]) -> Path:
        return _write_json(self.custom_parameters_path, dict(parameters))

    def read_custom_parameters(self) -> dict[str, Any]:
        return _read_json_file(self.custom_parameters_path, expected_type=dict)

    def write_plan(
        self,
        *,
        immediate_local_step: str,
        assignments: Sequence[SubAgentAssignmentDTO],
        integration_criteria: Sequence[str],
    ) -> Path:
        return _write_json(
            self.plan_path,
            {
                "immediate_local_step": immediate_local_step.strip(),
                "assignments": [assignment.to_dict() for assignment in assignments],
                "integration_criteria": [str(item).strip() for item in integration_criteria if str(item).strip()],
                "updated_at": utc_now_z(),
            },
        )

    def read_plan(self) -> dict[str, Any]:
        return _read_json_file(self.plan_path, expected_type=dict)

    def append_worker_output(self, payload: Mapping[str, Any]) -> None:
        records = _read_json_file(self.worker_outputs_path, expected_type=list)
        records.append(dict(payload))
        _write_json(self.worker_outputs_path, records)

    def read_worker_outputs(self) -> list[dict[str, Any]]:
        return _read_json_file(self.worker_outputs_path, expected_type=list)

    def write_integration_summary(self, payload: Mapping[str, Any]) -> Path:
        return _write_json(self.integration_summary_path, dict(payload))

    def read_integration_summary(self) -> dict[str, Any]:
        return _read_json_file(self.integration_summary_path, expected_type=dict)

    def append_execution_log(self, payload: Mapping[str, Any]) -> None:
        with self.execution_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(payload), sort_keys=True))
            handle.write("\n")

    def read_execution_log(self) -> list[dict[str, Any]]:
        return [
            json.loads(line)
            for line in self.execution_log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ] if self.execution_log_path.exists() else []

    def write_readme(self, content: str) -> Path:
        return _write_text(self.readme_path, content)

    def read_readme(self) -> str:
        return _read_optional_text(self.readme_path)

    def build_state_snapshot(self) -> dict[str, Any]:
        plan = self.read_plan()
        worker_outputs = self.read_worker_outputs()
        integration_summary = self.read_integration_summary()
        assignments = plan.get("assignments", [])
        return {
            "objective": self.read_objective(),
            "current_context_present": bool(self.read_current_context()),
            "available_agent_types": _coerce_string_list(self.read_custom_parameters().get("available_agent_types", "")),
            "immediate_local_step": plan.get("immediate_local_step"),
            "assignment_count": len(assignments) if isinstance(assignments, list) else 0,
            "worker_output_count": len(worker_outputs),
            "integration_ready": bool(worker_outputs),
            "final_response_present": bool(integration_summary.get("final_response")),
        }


def normalize_spawn_subagents_runtime_parameters(parameters: Mapping[str, Any]) -> dict[str, Any]:
    return SPAWN_SPECIALIZED_SUBAGENTS_HARNESS_MANIFEST.coerce_runtime_parameters(parameters)


def normalize_spawn_subagents_custom_parameters(parameters: Mapping[str, Any]) -> dict[str, Any]:
    return SPAWN_SPECIALIZED_SUBAGENTS_HARNESS_MANIFEST.coerce_custom_parameters(parameters)


SPAWN_SPECIALIZED_SUBAGENTS_HARNESS_MANIFEST = HarnessManifest(
    manifest_id="spawn_specialized_subagents",
    agent_name="spawn_specialized_subagents_agent",
    display_name="Spawn Specialized Subagents",
    module_path="harnessiq.agents.spawn_specialized_subagents",
    class_name="SpawnSpecializedSubagentsAgent",
    cli_command=None,
    cli_adapter_path="harnessiq.cli.adapters.spawn_specialized_subagents:SpawnSpecializedSubagentsHarnessCliAdapter",
    default_memory_root="memory/spawn_specialized_subagents",
    prompt_path="harnessiq/master_prompts/prompts/spawn_specialized_subagents.json",
    runtime_parameters=(
        HarnessParameterSpec("max_tokens", "integer", "Maximum model context budget for the spawn-specialized-subagents harness.", default=DEFAULT_AGENT_MAX_TOKENS),
        HarnessParameterSpec("reset_threshold", "number", "Fraction of max_tokens that triggers an automatic transcript reset.", default=DEFAULT_SPAWN_SUBAGENTS_RESET_THRESHOLD),
    ),
    custom_parameters=(
        HarnessParameterSpec("objective", "string", "Primary objective the orchestration harness must decompose and solve."),
        HarnessParameterSpec("available_agent_types", "string", "Comma-delimited list of worker archetypes available to the harness.", default="", nullable=True),
    ),
    memory_files=(
        HarnessMemoryFileSpec("objective", OBJECTIVE_FILENAME, "Primary orchestration objective.", format="markdown"),
        HarnessMemoryFileSpec("current_context", CURRENT_CONTEXT_FILENAME, "Current context and constraints supplied to the orchestrator.", format="markdown"),
        HarnessMemoryFileSpec("additional_prompt", ADDITIONAL_PROMPT_FILENAME, "Optional extra operator guidance appended to the prompt.", format="markdown"),
        HarnessMemoryFileSpec("plan", PLAN_FILENAME, "Current delegation plan with immediate local step and assignments.", format="json"),
        HarnessMemoryFileSpec("worker_outputs", WORKER_OUTPUTS_FILENAME, "Collected worker-stage outputs awaiting or after integration.", format="json"),
        HarnessMemoryFileSpec("integration_summary", INTEGRATION_SUMMARY_FILENAME, "Integrated final response and acceptance decisions.", format="json"),
        HarnessMemoryFileSpec("execution_log", EXECUTION_LOG_FILENAME, "Append-only orchestration event log.", format="jsonl"),
        HarnessMemoryFileSpec("readme", README_FILENAME, "Human-readable orchestration summary.", format="markdown"),
        HarnessMemoryFileSpec("runtime_parameters", RUNTIME_PARAMETERS_FILENAME, "Persisted typed runtime parameters.", format="json"),
        HarnessMemoryFileSpec("custom_parameters", CUSTOM_PARAMETERS_FILENAME, "Persisted typed custom parameters.", format="json"),
    ),
    output_schema={
        "type": "object",
        "properties": {
            "objective": {"type": "string"},
            "immediate_local_step": {"type": ["string", "null"]},
            "assignment_count": {"type": "integer"},
            "worker_output_count": {"type": "integer"},
            "final_response": {"type": ["string", "null"]},
        },
        "additionalProperties": False,
    },
)


def _ensure_json_file(path: Path, default_payload: Any) -> None:
    if not path.exists():
        _write_json(path, default_payload)


def _ensure_text_file(path: Path, default_content: str) -> None:
    if not path.exists():
        _write_text(path, default_content)


def _write_json(path: Path, payload: Any) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _write_text(path: Path, content: str) -> Path:
    rendered = content if not content or content.endswith("\n") else f"{content}\n"
    path.write_text(rendered, encoding="utf-8")
    return path


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


def _coerce_string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if not isinstance(value, (list, tuple)):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _read_optional_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def utc_now_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = [
    "ADDITIONAL_PROMPT_FILENAME",
    "CURRENT_CONTEXT_FILENAME",
    "CUSTOM_PARAMETERS_FILENAME",
    "DEFAULT_SPAWN_SUBAGENTS_RESET_THRESHOLD",
    "EXECUTION_LOG_FILENAME",
    "INTEGRATION_SUMMARY_FILENAME",
    "OBJECTIVE_FILENAME",
    "PLAN_FILENAME",
    "README_FILENAME",
    "RUNTIME_PARAMETERS_FILENAME",
    "SPAWN_SPECIALIZED_SUBAGENTS_HARNESS_MANIFEST",
    "SPAWN_SPECIALIZED_SUBAGENTS_PROMPT_KEY",
    "SpawnSpecializedSubagentsConfig",
    "SpawnSpecializedSubagentsMemoryStore",
    "WORKER_OUTPUTS_FILENAME",
    "normalize_spawn_subagents_custom_parameters",
    "normalize_spawn_subagents_runtime_parameters",
]
