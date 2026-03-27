"""Shared contracts and durable memory store for the mission-driven harness."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Mapping

from harnessiq.shared.agents import DEFAULT_AGENT_MAX_TOKENS
from harnessiq.shared.harness_manifest import HarnessManifest, HarnessMemoryFileSpec, HarnessParameterSpec

MissionType = Literal["app_build", "migration", "research"]
MissionTaskStatus = Literal["pending", "in_progress", "complete", "blocked", "skipped"]

DEFAULT_MISSION_DRIVEN_RESET_THRESHOLD = 0.85
MISSION_FILENAME = "mission.json"
TASK_PLAN_FILENAME = "task_plan.json"
MEMORY_STORE_FILENAME = "memory_store.json"
DECISION_LOG_FILENAME = "decision_log.json"
FILE_MANIFEST_FILENAME = "file_manifest.json"
ERROR_LOG_FILENAME = "error_log.json"
FEEDBACK_LOG_FILENAME = "feedback_log.json"
TEST_RESULTS_FILENAME = "test_results.json"
ARTIFACTS_FILENAME = "artifacts.json"
TOOL_CALL_HISTORY_FILENAME = "tool_call_history.json"
RESEARCH_LOG_FILENAME = "research_log.json"
NEXT_ACTIONS_FILENAME = "next_actions.json"
MISSION_STATUS_FILENAME = "mission_status.json"
PROGRESS_LOG_FILENAME = "progress_log.jsonl"
README_FILENAME = "README.md"
CHECKPOINTS_DIRNAME = "checkpoints"
ADDITIONAL_PROMPT_FILENAME = "additional_prompt.md"
RUNTIME_PARAMETERS_FILENAME = "runtime_parameters.json"
CUSTOM_PARAMETERS_FILENAME = "custom_parameters.json"
MISSION_DRIVEN_PROMPT_KEY = "mission_driven"


@dataclass(frozen=True, slots=True)
class MissionDefinition:
    """Immutable mission definition written to disk as the scope contract."""

    goal: str
    mission_type: str
    success_criteria: tuple[str, ...] = ()
    in_scope: tuple[str, ...] = ()
    out_of_scope: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()
    authorization_level: str = ""
    human_contact: str = ""
    amended_at: str | None = None
    amendment_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "mission_type": self.mission_type,
            "success_criteria": list(self.success_criteria),
            "scope": {
                "in_scope": list(self.in_scope),
                "out_of_scope": list(self.out_of_scope),
            },
            "constraints": list(self.constraints),
            "authorization_level": self.authorization_level,
            "human_contact": self.human_contact,
            "amended_at": self.amended_at,
            "amendment_reason": self.amendment_reason,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MissionDefinition":
        scope = payload.get("scope", {})
        return cls(
            goal=str(payload.get("goal", "")).strip(),
            mission_type=str(payload.get("mission_type", "")).strip(),
            success_criteria=tuple(_coerce_string_list(payload.get("success_criteria", ()))),
            in_scope=tuple(_coerce_string_list(scope.get("in_scope", ()) if isinstance(scope, Mapping) else ())),
            out_of_scope=tuple(
                _coerce_string_list(scope.get("out_of_scope", ()) if isinstance(scope, Mapping) else ())
            ),
            constraints=tuple(_coerce_string_list(payload.get("constraints", ()))),
            authorization_level=str(payload.get("authorization_level", "")).strip(),
            human_contact=str(payload.get("human_contact", "")).strip(),
            amended_at=_coerce_optional_string(payload.get("amended_at")),
            amendment_reason=_coerce_optional_string(payload.get("amendment_reason")),
        )


@dataclass(frozen=True, slots=True)
class MissionTask:
    """One hierarchical task item in the mission task plan."""

    task_id: str
    title: str
    description: str
    status: MissionTaskStatus = "pending"
    prerequisites: tuple[str, ...] = ()
    complexity: str = "medium"
    assigned_to_session: str | None = None
    completed_at: str | None = None
    blocked_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.task_id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "prerequisites": list(self.prerequisites),
            "complexity": self.complexity,
            "assigned_to_session": self.assigned_to_session,
            "completed_at": self.completed_at,
            "blocked_reason": self.blocked_reason,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MissionTask":
        return cls(
            task_id=str(payload.get("id", "")).strip(),
            title=str(payload.get("title", "")).strip(),
            description=str(payload.get("description", "")).strip(),
            status=str(payload.get("status", "pending")),  # type: ignore[arg-type]
            prerequisites=tuple(_coerce_string_list(payload.get("prerequisites", ()))),
            complexity=str(payload.get("complexity", "medium")).strip() or "medium",
            assigned_to_session=_coerce_optional_string(payload.get("assigned_to_session")),
            completed_at=_coerce_optional_string(payload.get("completed_at")),
            blocked_reason=_coerce_optional_string(payload.get("blocked_reason")),
        )


@dataclass(frozen=True, slots=True)
class MissionTaskPlan:
    """Top-level task-plan document for the mission-driven harness."""

    tasks: tuple[MissionTask, ...] = ()
    current_task_pointer: str | None = None
    last_updated: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "tasks": [task.to_dict() for task in self.tasks],
            "current_task_pointer": self.current_task_pointer,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MissionTaskPlan":
        raw_tasks = payload.get("tasks", ())
        return cls(
            tasks=tuple(
                MissionTask.from_dict(item)
                for item in raw_tasks
                if isinstance(item, Mapping)
            ),
            current_task_pointer=_coerce_optional_string(payload.get("current_task_pointer")),
            last_updated=str(payload.get("last_updated", "")).strip(),
        )


@dataclass(frozen=True, slots=True)
class MissionDrivenAgentConfig:
    """Runtime configuration for one mission-driven harness instance."""

    memory_path: Path
    mission_goal: str
    mission_type: MissionType
    additional_prompt: str = ""
    max_tokens: int = DEFAULT_AGENT_MAX_TOKENS
    reset_threshold: float = DEFAULT_MISSION_DRIVEN_RESET_THRESHOLD

    def __post_init__(self) -> None:
        object.__setattr__(self, "memory_path", Path(self.memory_path))
        normalized_goal = self.mission_goal.strip()
        if not normalized_goal:
            raise ValueError("mission_goal must not be blank.")
        normalized_type = str(self.mission_type).strip()
        if normalized_type not in {"app_build", "migration", "research"}:
            raise ValueError("mission_type must be one of: app_build, migration, research.")
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be greater than zero.")
        if not 0 < self.reset_threshold <= 1:
            raise ValueError("reset_threshold must be between 0 and 1.")
        object.__setattr__(self, "mission_goal", normalized_goal)
        object.__setattr__(self, "mission_type", normalized_type)
        object.__setattr__(self, "additional_prompt", self.additional_prompt.strip())


@dataclass(slots=True)
class MissionDrivenMemoryStore:
    """File-backed mission artifact store that mirrors the prompt contract."""

    memory_path: Path

    def __post_init__(self) -> None:
        self.memory_path = Path(self.memory_path)

    @property
    def mission_path(self) -> Path:
        return self.memory_path / MISSION_FILENAME

    @property
    def task_plan_path(self) -> Path:
        return self.memory_path / TASK_PLAN_FILENAME

    @property
    def memory_store_path(self) -> Path:
        return self.memory_path / MEMORY_STORE_FILENAME

    @property
    def decision_log_path(self) -> Path:
        return self.memory_path / DECISION_LOG_FILENAME

    @property
    def file_manifest_path(self) -> Path:
        return self.memory_path / FILE_MANIFEST_FILENAME

    @property
    def error_log_path(self) -> Path:
        return self.memory_path / ERROR_LOG_FILENAME

    @property
    def feedback_log_path(self) -> Path:
        return self.memory_path / FEEDBACK_LOG_FILENAME

    @property
    def test_results_path(self) -> Path:
        return self.memory_path / TEST_RESULTS_FILENAME

    @property
    def artifacts_path(self) -> Path:
        return self.memory_path / ARTIFACTS_FILENAME

    @property
    def tool_call_history_path(self) -> Path:
        return self.memory_path / TOOL_CALL_HISTORY_FILENAME

    @property
    def research_log_path(self) -> Path:
        return self.memory_path / RESEARCH_LOG_FILENAME

    @property
    def next_actions_path(self) -> Path:
        return self.memory_path / NEXT_ACTIONS_FILENAME

    @property
    def mission_status_path(self) -> Path:
        return self.memory_path / MISSION_STATUS_FILENAME

    @property
    def progress_log_path(self) -> Path:
        return self.memory_path / PROGRESS_LOG_FILENAME

    @property
    def readme_path(self) -> Path:
        return self.memory_path / README_FILENAME

    @property
    def checkpoints_path(self) -> Path:
        return self.memory_path / CHECKPOINTS_DIRNAME

    @property
    def additional_prompt_path(self) -> Path:
        return self.memory_path / ADDITIONAL_PROMPT_FILENAME

    @property
    def runtime_parameters_path(self) -> Path:
        return self.memory_path / RUNTIME_PARAMETERS_FILENAME

    @property
    def custom_parameters_path(self) -> Path:
        return self.memory_path / CUSTOM_PARAMETERS_FILENAME

    def prepare(self) -> None:
        self.memory_path.mkdir(parents=True, exist_ok=True)
        self.checkpoints_path.mkdir(parents=True, exist_ok=True)
        _ensure_json_file(self.mission_path, {})
        _ensure_json_file(self.task_plan_path, {"tasks": [], "current_task_pointer": None, "last_updated": ""})
        _ensure_json_file(self.memory_store_path, [])
        _ensure_json_file(self.decision_log_path, [])
        _ensure_json_file(self.file_manifest_path, [])
        _ensure_json_file(self.error_log_path, [])
        _ensure_json_file(self.feedback_log_path, [])
        _ensure_json_file(self.test_results_path, [])
        _ensure_json_file(self.artifacts_path, [])
        _ensure_json_file(self.tool_call_history_path, [])
        _ensure_json_file(self.research_log_path, [])
        _ensure_json_file(self.next_actions_path, [])
        _ensure_json_file(
            self.mission_status_path,
            {
                "mission_status": None,
                "current_task_pointer": None,
                "next_actions": [],
                "updated_at": "",
            },
        )
        _ensure_text_file(self.progress_log_path, "")
        _ensure_text_file(self.readme_path, "")
        _ensure_text_file(self.additional_prompt_path, "")
        _ensure_json_file(self.runtime_parameters_path, {})
        _ensure_json_file(self.custom_parameters_path, {})

    def is_initialized(self) -> bool:
        payload = self.read_mission()
        return bool(payload.get("definition")) and bool(self.read_task_plan().tasks)

    def write_runtime_parameters(self, parameters: Mapping[str, Any]) -> Path:
        return _write_json(self.runtime_parameters_path, dict(parameters))

    def read_runtime_parameters(self) -> dict[str, Any]:
        return _read_json_file(self.runtime_parameters_path, expected_type=dict)

    def write_custom_parameters(self, parameters: Mapping[str, Any]) -> Path:
        return _write_json(self.custom_parameters_path, dict(parameters))

    def read_custom_parameters(self) -> dict[str, Any]:
        return _read_json_file(self.custom_parameters_path, expected_type=dict)

    def write_additional_prompt(self, content: str) -> Path:
        return _write_text(self.additional_prompt_path, content)

    def read_additional_prompt(self) -> str:
        return _read_optional_text(self.additional_prompt_path)

    def read_mission(self) -> dict[str, Any]:
        return _read_json_file(self.mission_path, expected_type=dict)

    def write_mission(
        self,
        *,
        definition: MissionDefinition,
        mission_status: str,
        current_task_pointer: str | None = None,
        next_actions: list[str],
    ) -> Path:
        payload = {
            "definition": definition.to_dict(),
            "mission_status": mission_status,
            "next_actions": list(next_actions),
        }
        path = _write_json(self.mission_path, payload)
        self.write_next_actions(next_actions)
        self.write_mission_status_record(
            mission_status=mission_status,
            current_task_pointer=current_task_pointer,
            next_actions=next_actions,
        )
        return path

    def update_mission_status(
        self,
        mission_status: str,
        *,
        current_task_pointer: str | None = None,
        next_actions: list[str] | None = None,
    ) -> Path:
        payload = self.read_mission()
        payload["mission_status"] = mission_status
        if next_actions is not None:
            payload["next_actions"] = list(next_actions)
            self.write_next_actions(next_actions)
        path = _write_json(self.mission_path, payload)
        self.write_mission_status_record(
            mission_status=mission_status,
            current_task_pointer=current_task_pointer,
            next_actions=list(next_actions or payload.get("next_actions", [])),
        )
        return path

    def write_next_actions(self, next_actions: list[str]) -> Path:
        return _write_json(self.next_actions_path, [str(item).strip() for item in next_actions if str(item).strip()])

    def read_next_actions(self) -> list[str]:
        return _read_json_file(self.next_actions_path, expected_type=list)

    def write_mission_status_record(
        self,
        *,
        mission_status: str,
        current_task_pointer: str | None,
        next_actions: list[str],
    ) -> Path:
        return _write_json(
            self.mission_status_path,
            {
                "mission_status": mission_status,
                "current_task_pointer": current_task_pointer,
                "next_actions": [str(item).strip() for item in next_actions if str(item).strip()],
                "updated_at": utc_now_z(),
            },
        )

    def read_mission_status_record(self) -> dict[str, Any]:
        return _read_json_file(self.mission_status_path, expected_type=dict)

    def read_task_plan(self) -> MissionTaskPlan:
        return MissionTaskPlan.from_dict(_read_json_file(self.task_plan_path, expected_type=dict))

    def write_task_plan(self, plan: MissionTaskPlan) -> Path:
        return _write_json(self.task_plan_path, plan.to_dict())

    def write_readme(self, content: str) -> Path:
        return _write_text(self.readme_path, content)

    def read_readme(self) -> str:
        return _read_optional_text(self.readme_path)

    def read_progress_events(self) -> list[dict[str, Any]]:
        return [
            json.loads(line)
            for line in self.progress_log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ] if self.progress_log_path.exists() else []

    def append_progress_event(self, record: Mapping[str, Any]) -> None:
        with self.progress_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(record), sort_keys=True))
            handle.write("\n")

    def append_memory_facts(self, records: list[Mapping[str, Any]]) -> None:
        self._append_json_records(self.memory_store_path, records)

    def read_memory_facts(self) -> list[dict[str, Any]]:
        return _read_json_file(self.memory_store_path, expected_type=list)

    def append_decisions(self, records: list[Mapping[str, Any]]) -> None:
        self._append_json_records(self.decision_log_path, records)

    def read_decisions(self) -> list[dict[str, Any]]:
        return _read_json_file(self.decision_log_path, expected_type=list)

    def append_error_records(self, records: list[Mapping[str, Any]]) -> None:
        self._append_json_records(self.error_log_path, records)

    def read_error_records(self) -> list[dict[str, Any]]:
        return _read_json_file(self.error_log_path, expected_type=list)

    def append_feedback_records(self, records: list[Mapping[str, Any]]) -> None:
        self._append_json_records(self.feedback_log_path, records)

    def read_feedback_records(self) -> list[dict[str, Any]]:
        return _read_json_file(self.feedback_log_path, expected_type=list)

    def append_test_results(self, records: list[Mapping[str, Any]]) -> None:
        self._append_json_records(self.test_results_path, records)

    def read_test_results(self) -> list[dict[str, Any]]:
        return _read_json_file(self.test_results_path, expected_type=list)

    def append_artifact_records(self, records: list[Mapping[str, Any]]) -> None:
        payload = _read_json_file(self.artifacts_path, expected_type=list)
        for record in records:
            normalized = dict(record)
            path_value = normalized.get("path")
            if isinstance(path_value, str) and path_value:
                artifact_path = Path(path_value)
                if artifact_path.exists() and "content_hash" not in normalized:
                    normalized["content_hash"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
                    normalized["size_bytes"] = artifact_path.stat().st_size
            payload.append(normalized)
        _write_json(self.artifacts_path, payload)

    def read_artifact_records(self) -> list[dict[str, Any]]:
        return _read_json_file(self.artifacts_path, expected_type=list)

    def write_file_manifest(self, records: list[Mapping[str, Any]]) -> Path:
        return _write_json(
            self.file_manifest_path,
            [self._normalize_file_manifest_record(record) for record in records],
        )

    def read_file_manifest(self) -> list[dict[str, Any]]:
        return _read_json_file(self.file_manifest_path, expected_type=list)

    def merge_file_manifest_records(self, records: list[Mapping[str, Any]]) -> Path:
        indexed: dict[str, dict[str, Any]] = {}
        for existing in self.read_file_manifest():
            key = str(existing.get("path") or existing.get("key") or "").strip()
            if key:
                indexed[key] = dict(existing)
        for record in records:
            normalized = self._normalize_file_manifest_record(record)
            key = str(normalized.get("path") or normalized.get("key") or "").strip()
            if not key:
                continue
            indexed[key] = {**indexed.get(key, {}), **normalized}
        ordered = [indexed[key] for key in sorted(indexed)]
        return _write_json(self.file_manifest_path, ordered)

    def append_tool_call_records(self, records: list[Mapping[str, Any]]) -> None:
        self._append_json_records(self.tool_call_history_path, records)

    def read_tool_call_records(self) -> list[dict[str, Any]]:
        return _read_json_file(self.tool_call_history_path, expected_type=list)

    def append_research_records(self, records: list[Mapping[str, Any]]) -> None:
        self._append_json_records(self.research_log_path, records)

    def read_research_records(self) -> list[dict[str, Any]]:
        return _read_json_file(self.research_log_path, expected_type=list)

    def initialize_artifact(
        self,
        *,
        definition: MissionDefinition,
        task_plan: MissionTaskPlan,
        narrative: str,
        session_id: str,
        next_actions: list[str],
    ) -> None:
        self.write_mission(
            definition=definition,
            mission_status="active",
            current_task_pointer=task_plan.current_task_pointer,
            next_actions=next_actions,
        )
        self.write_task_plan(task_plan)
        self.write_readme(narrative)
        self.append_progress_event(
            {
                "timestamp": utc_now_z(),
                "task_id": None,
                "event_type": "session_started",
                "from_status": None,
                "to_status": "active",
                "summary": "Mission artifact initialized and ready for execution.",
                "session_id": session_id,
            }
        )

    def create_checkpoint(self, *, checkpoint_name: str, resume_instructions: str) -> Path:
        snapshot = {
            "mission": self.read_mission(),
            "task_plan": self.read_task_plan().to_dict(),
            "memory_store": self.read_memory_facts(),
            "decision_log": self.read_decisions(),
            "file_manifest": self.read_file_manifest(),
            "error_log": self.read_error_records(),
            "feedback_log": self.read_feedback_records(),
            "test_results": self.read_test_results(),
            "artifacts": self.read_artifact_records(),
            "tool_call_history": self.read_tool_call_records(),
            "research_log": self.read_research_records(),
            "next_actions": self.read_next_actions(),
            "mission_status_record": self.read_mission_status_record(),
            "progress_log": self.read_progress_events(),
            "readme": self.read_readme(),
            "resume_instructions": resume_instructions.strip(),
            "saved_at": utc_now_z(),
        }
        safe_name = checkpoint_name.strip().replace(" ", "_") or "checkpoint"
        target = self.checkpoints_path / f"{safe_name}_{utc_now_z().replace(':', '').replace('-', '')}.json"
        _write_json(target, snapshot)
        return target

    def build_state_snapshot(self) -> dict[str, Any]:
        mission = self.read_mission()
        task_plan = self.read_task_plan()
        tasks = list(task_plan.tasks)
        mission_status_record = self.read_mission_status_record()
        return {
            "mission_status": mission_status_record.get("mission_status", mission.get("mission_status")),
            "mission_goal": mission.get("definition", {}).get("goal"),
            "mission_type": mission.get("definition", {}).get("mission_type"),
            "current_task_pointer": mission_status_record.get("current_task_pointer", task_plan.current_task_pointer),
            "next_actions": self.read_next_actions() or mission.get("next_actions", []),
            "task_count": len(tasks),
            "completed_task_count": sum(1 for task in tasks if task.status == "complete"),
            "blocked_task_count": sum(1 for task in tasks if task.status == "blocked"),
            "decision_count": len(self.read_decisions()),
            "memory_fact_count": len(self.read_memory_facts()),
            "test_result_count": len(self.read_test_results()),
            "artifact_count": len(self.read_artifact_records()),
            "file_record_count": len(self.read_file_manifest()),
            "research_entry_count": len(self.read_research_records()),
            "tool_call_count": len(self.read_tool_call_records()),
        }

    def _normalize_file_manifest_record(self, record: Mapping[str, Any]) -> dict[str, Any]:
        path_value = str(record.get("path", "")).strip()
        return {
            "key": str(record.get("key", "")).strip() or None,
            "path": path_value,
            "exists": bool(record.get("exists", True)),
            "kind": str(record.get("kind", "file")).strip() or "file",
            "format": str(record.get("format", "other")).strip() or "other",
            "purpose": str(record.get("purpose", "")).strip(),
            "change_type": str(record.get("change_type", "updated")).strip() or "updated",
            "dependencies": _coerce_string_list(record.get("dependencies", [])),
            "dependents": _coerce_string_list(record.get("dependents", [])),
            "summary": str(record.get("summary", "")).strip(),
            "updated_at": str(record.get("updated_at", utc_now_z())).strip() or utc_now_z(),
        }

    def _append_json_records(self, path: Path, records: list[Mapping[str, Any]]) -> None:
        payload = _read_json_file(path, expected_type=list)
        payload.extend(dict(record) for record in records)
        _write_json(path, payload)


def normalize_mission_driven_runtime_parameters(parameters: Mapping[str, Any]) -> dict[str, Any]:
    return MISSION_DRIVEN_HARNESS_MANIFEST.coerce_runtime_parameters(parameters)


def normalize_mission_driven_custom_parameters(parameters: Mapping[str, Any]) -> dict[str, Any]:
    payload = MISSION_DRIVEN_HARNESS_MANIFEST.coerce_custom_parameters(parameters)
    mission_type = payload.get("mission_type")
    if mission_type not in {"app_build", "migration", "research"}:
        raise ValueError("mission_type must be one of: app_build, migration, research.")
    return payload


MISSION_DRIVEN_HARNESS_MANIFEST = HarnessManifest(
    manifest_id="mission_driven",
    agent_name="mission_driven_agent",
    display_name="Mission Driven",
    module_path="harnessiq.agents.mission_driven",
    class_name="MissionDrivenAgent",
    cli_command=None,
    cli_adapter_path="harnessiq.cli.adapters.mission_driven:MissionDrivenHarnessCliAdapter",
    default_memory_root="memory/mission_driven",
    prompt_path="harnessiq/master_prompts/prompts/mission_driven.json",
    runtime_parameters=(
        HarnessParameterSpec("max_tokens", "integer", "Maximum model context budget for the mission-driven harness.", default=DEFAULT_AGENT_MAX_TOKENS),
        HarnessParameterSpec("reset_threshold", "number", "Fraction of max_tokens that triggers an automatic transcript reset.", default=DEFAULT_MISSION_DRIVEN_RESET_THRESHOLD),
    ),
    custom_parameters=(
        HarnessParameterSpec("mission_goal", "string", "Top-level mission goal the harness should decompose and execute."),
        HarnessParameterSpec("mission_type", "string", "Mission type that calibrates the artifact threat model.", choices=("app_build", "migration", "research")),
    ),
    memory_files=(
        HarnessMemoryFileSpec("mission", MISSION_FILENAME, "Mission definition and aggregate mission status.", format="json"),
        HarnessMemoryFileSpec("task_plan", TASK_PLAN_FILENAME, "Hierarchical task plan with task pointer and statuses.", format="json"),
        HarnessMemoryFileSpec("memory_store", MEMORY_STORE_FILENAME, "Durable fact registry used across mission sessions.", format="json"),
        HarnessMemoryFileSpec("decision_log", DECISION_LOG_FILENAME, "Decision records and rationale.", format="json"),
        HarnessMemoryFileSpec("file_manifest", FILE_MANIFEST_FILENAME, "Registry of files created or modified by the mission.", format="json"),
        HarnessMemoryFileSpec("error_log", ERROR_LOG_FILENAME, "Errors, blockers, and retries encountered during the mission.", format="json"),
        HarnessMemoryFileSpec("feedback_log", FEEDBACK_LOG_FILENAME, "Human feedback and approval records.", format="json"),
        HarnessMemoryFileSpec("test_results", TEST_RESULTS_FILENAME, "Recorded validation results for mission tasks.", format="json"),
        HarnessMemoryFileSpec("artifacts", ARTIFACTS_FILENAME, "Registered output artifacts and deliverables.", format="json"),
        HarnessMemoryFileSpec("tool_call_history", TOOL_CALL_HISTORY_FILENAME, "Structured history of mission-tool calls and results.", format="json"),
        HarnessMemoryFileSpec("research_log", RESEARCH_LOG_FILENAME, "Durable research findings and external references gathered during the mission.", format="json"),
        HarnessMemoryFileSpec("next_actions", NEXT_ACTIONS_FILENAME, "Prioritized next-action queue for the active mission state.", format="json"),
        HarnessMemoryFileSpec("mission_status_record", MISSION_STATUS_FILENAME, "Dedicated mission status snapshot and current task pointer.", format="json"),
        HarnessMemoryFileSpec("progress_log", PROGRESS_LOG_FILENAME, "Append-only mission event journal.", format="jsonl"),
        HarnessMemoryFileSpec("readme", README_FILENAME, "Human-readable mission narrative summary.", format="markdown"),
        HarnessMemoryFileSpec("checkpoints", CHECKPOINTS_DIRNAME, "Checkpoint snapshots for resumability and rollback.", kind="directory", format="directory"),
        HarnessMemoryFileSpec("additional_prompt", ADDITIONAL_PROMPT_FILENAME, "Optional extra operator guidance appended to the harness prompt.", format="markdown"),
        HarnessMemoryFileSpec("runtime_parameters", RUNTIME_PARAMETERS_FILENAME, "Persisted typed runtime parameters.", format="json"),
        HarnessMemoryFileSpec("custom_parameters", CUSTOM_PARAMETERS_FILENAME, "Persisted typed custom parameters.", format="json"),
    ),
    output_schema={
        "type": "object",
        "properties": {
            "mission_status": {"type": ["string", "null"]},
            "mission_goal": {"type": ["string", "null"]},
            "mission_type": {"type": ["string", "null"]},
            "current_task_pointer": {"type": ["string", "null"]},
            "next_actions": {"type": "array", "items": {"type": "string"}},
            "task_count": {"type": "integer"},
            "completed_task_count": {"type": "integer"},
            "blocked_task_count": {"type": "integer"},
            "artifact_count": {"type": "integer"},
            "file_record_count": {"type": "integer"},
            "research_entry_count": {"type": "integer"},
            "tool_call_count": {"type": "integer"},
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
    if not isinstance(value, (list, tuple)):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _coerce_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _read_optional_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def utc_now_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = [
    "ADDITIONAL_PROMPT_FILENAME",
    "ARTIFACTS_FILENAME",
    "CHECKPOINTS_DIRNAME",
    "CUSTOM_PARAMETERS_FILENAME",
    "DECISION_LOG_FILENAME",
    "DEFAULT_MISSION_DRIVEN_RESET_THRESHOLD",
    "ERROR_LOG_FILENAME",
    "FEEDBACK_LOG_FILENAME",
    "FILE_MANIFEST_FILENAME",
    "MEMORY_STORE_FILENAME",
    "MISSION_DRIVEN_HARNESS_MANIFEST",
    "MISSION_DRIVEN_PROMPT_KEY",
    "MISSION_FILENAME",
    "MISSION_STATUS_FILENAME",
    "MissionDefinition",
    "MissionDrivenAgentConfig",
    "MissionDrivenMemoryStore",
    "MissionTask",
    "MissionTaskPlan",
    "NEXT_ACTIONS_FILENAME",
    "PROGRESS_LOG_FILENAME",
    "README_FILENAME",
    "RESEARCH_LOG_FILENAME",
    "RUNTIME_PARAMETERS_FILENAME",
    "TASK_PLAN_FILENAME",
    "TEST_RESULTS_FILENAME",
    "TOOL_CALL_HISTORY_FILENAME",
    "normalize_mission_driven_custom_parameters",
    "normalize_mission_driven_runtime_parameters",
]
