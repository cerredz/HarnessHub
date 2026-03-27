"""Concrete mission-driven harness implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from harnessiq.agents.base import BaseAgent
from harnessiq.agents.helpers import find_repo_root, resolve_memory_path, utc_now_z
from harnessiq.agents.mission_driven.stages import (
    MissionDefinitionStage,
    MissionNarrativeStage,
    MissionStatusStage,
    MissionTaskPlanStage,
)
from harnessiq.agents.subcalls import JsonSubcallRunner
from harnessiq.shared.agents import (
    AgentModel,
    AgentParameterSection,
    AgentRuntimeConfig,
    json_parameter_section,
    merge_agent_runtime_config,
)
from harnessiq.shared.dtos.prompt_harnesses import MissionDrivenInstancePayload
from harnessiq.shared.exceptions import ValidationError
from harnessiq.shared.mission_driven import (
    DEFAULT_MISSION_DRIVEN_RESET_THRESHOLD,
    MISSION_DRIVEN_HARNESS_MANIFEST,
    MissionDefinition,
    MissionDrivenAgentConfig,
    MissionDrivenMemoryStore,
    MissionTask,
    MissionTaskPlan,
    normalize_mission_driven_custom_parameters,
    normalize_mission_driven_runtime_parameters,
)
from harnessiq.shared.tools import (
    MISSION_CREATE_CHECKPOINT,
    MISSION_INITIALIZE_ARTIFACT,
    MISSION_RECORD_UPDATES,
    RegisteredTool,
    ToolDefinition,
)
from harnessiq.tools.registry import create_tool_registry

_DEFAULT_MEMORY_PATH = Path(MISSION_DRIVEN_HARNESS_MANIFEST.resolved_default_memory_root)


class MissionDrivenAgent(BaseAgent):
    """Reusable mission artifact harness built from the bundled master prompt."""

    def __init__(
        self,
        *,
        model: AgentModel,
        mission_goal: str,
        mission_type: str,
        memory_path: str | Path | None = None,
        additional_prompt: str = "",
        max_tokens: int = 80_000,
        reset_threshold: float = DEFAULT_MISSION_DRIVEN_RESET_THRESHOLD,
        tools: Sequence[RegisteredTool] | None = None,
        runtime_config: AgentRuntimeConfig | None = None,
        json_subcall_runner: JsonSubcallRunner | None = None,
        instance_name: str | None = None,
    ) -> None:
        resolved_memory_path = resolve_memory_path(memory_path, default_path=_DEFAULT_MEMORY_PATH)
        self._config = MissionDrivenAgentConfig(
            memory_path=resolved_memory_path,
            mission_goal=mission_goal,
            mission_type=mission_type,  # type: ignore[arg-type]
            additional_prompt=additional_prompt,
            max_tokens=max_tokens,
            reset_threshold=reset_threshold,
        )
        self._json_subcall_runner = json_subcall_runner
        self._memory_store = MissionDrivenMemoryStore(memory_path=resolved_memory_path)
        self._memory_store.prepare()
        self._memory_store.write_runtime_parameters(
            {"max_tokens": max_tokens, "reset_threshold": reset_threshold}
        )
        self._memory_store.write_custom_parameters(
            {"mission_goal": mission_goal, "mission_type": mission_type}
        )
        self._memory_store.write_additional_prompt(additional_prompt)
        tool_registry = create_tool_registry(self._build_internal_tools(), tuple(tools or ()))
        super().__init__(
            name="mission_driven_agent",
            model=model,
            tool_executor=tool_registry,
            runtime_config=merge_agent_runtime_config(
                runtime_config,
                max_tokens=max_tokens,
                reset_threshold=reset_threshold,
            ),
            memory_path=resolved_memory_path,
            repo_root=find_repo_root(resolved_memory_path),
            instance_name=instance_name,
        )
        self._memory_store = MissionDrivenMemoryStore(memory_path=self.memory_path)
        self._memory_store.prepare()
        self._definition_stage = MissionDefinitionStage(
            model=model,
            runner=json_subcall_runner,
            agent_name=self.name,
        )
        self._task_plan_stage = MissionTaskPlanStage(
            model=model,
            runner=json_subcall_runner,
            agent_name=self.name,
        )
        self._status_stage = MissionStatusStage(
            model=model,
            runner=json_subcall_runner,
            agent_name=self.name,
        )
        self._narrative_stage = MissionNarrativeStage(
            model=model,
            runner=json_subcall_runner,
            agent_name=self.name,
        )

    @property
    def config(self) -> MissionDrivenAgentConfig:
        return self._config

    @property
    def memory_store(self) -> MissionDrivenMemoryStore:
        return self._memory_store

    @classmethod
    def from_memory(
        cls,
        *,
        model: AgentModel,
        memory_path: str | Path | None = None,
        runtime_overrides: Mapping[str, Any] | None = None,
        custom_overrides: Mapping[str, Any] | None = None,
        tools: Sequence[RegisteredTool] | None = None,
        runtime_config: AgentRuntimeConfig | None = None,
        json_subcall_runner: JsonSubcallRunner | None = None,
        instance_name: str | None = None,
    ) -> "MissionDrivenAgent":
        resolved_memory_path = resolve_memory_path(memory_path, default_path=_DEFAULT_MEMORY_PATH)
        store = MissionDrivenMemoryStore(memory_path=resolved_memory_path)
        store.prepare()
        runtime_parameters = store.read_runtime_parameters()
        if runtime_overrides:
            runtime_parameters.update(runtime_overrides)
        custom_parameters = store.read_custom_parameters()
        if custom_overrides:
            custom_parameters.update(custom_overrides)
        normalized_runtime = normalize_mission_driven_runtime_parameters(runtime_parameters)
        normalized_custom = normalize_mission_driven_custom_parameters(custom_parameters)
        return cls(
            model=model,
            memory_path=resolved_memory_path,
            mission_goal=str(normalized_custom["mission_goal"]),
            mission_type=str(normalized_custom["mission_type"]),
            additional_prompt=store.read_additional_prompt(),
            tools=tools,
            runtime_config=runtime_config,
            json_subcall_runner=json_subcall_runner,
            instance_name=instance_name,
            **normalized_runtime,
        )

    def build_instance_payload(self) -> dict[str, Any]:
        return MissionDrivenInstancePayload(
            memory_path=self._config.memory_path,
            mission_goal=self._config.mission_goal,
            mission_type=self._config.mission_type,
            additional_prompt=self._config.additional_prompt,
            max_tokens=self._config.max_tokens,
            reset_threshold=self._config.reset_threshold,
        ).to_dict()

    def prepare(self) -> None:
        self._memory_store.prepare()
        self._memory_store.write_runtime_parameters(
            {"max_tokens": self._config.max_tokens, "reset_threshold": self._config.reset_threshold}
        )
        self._memory_store.write_custom_parameters(
            {"mission_goal": self._config.mission_goal, "mission_type": self._config.mission_type}
        )
        self._memory_store.write_additional_prompt(self._config.additional_prompt)
        if not self._memory_store.is_initialized():
            self._initialize_artifact()
        self._sync_file_manifest()

    def build_system_prompt(self) -> str:
        return (
            "You are MissionDrivenAgent. "
            "Maintain the durable mission artifact through the mission tools. "
            "Do not treat the artifact as conversational memory; persist every meaningful state change through tools."
        )

    def load_parameter_sections(self) -> Sequence[AgentParameterSection]:
        mission = self._memory_store.read_mission()
        task_plan = self._memory_store.read_task_plan()
        sections: list[AgentParameterSection] = [
            AgentParameterSection(title="Master Prompt", content=self._definition_stage._master_prompt()),
            json_parameter_section(
                "Mission Configuration",
                {
                    "mission_goal": self._config.mission_goal,
                    "mission_type": self._config.mission_type,
                },
            ),
            json_parameter_section("Mission Artifact Snapshot", self._memory_store.build_state_snapshot()),
            json_parameter_section("Mission", mission),
            json_parameter_section("Task Plan", task_plan.to_dict()),
        ]
        additional_prompt = self._memory_store.read_additional_prompt()
        if additional_prompt:
            sections.append(AgentParameterSection(title="Additional Prompt", content=additional_prompt))
        return tuple(sections)

    def build_ledger_outputs(self) -> dict[str, Any]:
        return self._memory_store.build_state_snapshot()

    def build_ledger_tags(self) -> list[str]:
        return ["mission", "durable-state", self._config.mission_type]

    def _build_internal_tools(self) -> tuple[RegisteredTool, ...]:
        return (
            RegisteredTool(
                definition=ToolDefinition(
                    key=MISSION_INITIALIZE_ARTIFACT,
                    name="initialize_artifact",
                    description="Initialize the full mission artifact from the configured mission goal and type.",
                    input_schema={"type": "object", "properties": {}, "required": [], "additionalProperties": False},
                ),
                handler=lambda arguments: self._handle_initialize_artifact(arguments),
            ),
            RegisteredTool(
                definition=ToolDefinition(
                    key=MISSION_RECORD_UPDATES,
                    name="record_updates",
                    description="Persist task, progress, fact, decision, test, feedback, and artifact updates into the mission artifact.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "task_updates": {"type": "array", "items": {"type": "object"}},
                            "progress_events": {"type": "array", "items": {"type": "object"}},
                            "memory_facts": {"type": "array", "items": {"type": "object"}},
                            "decisions": {"type": "array", "items": {"type": "object"}},
                            "errors": {"type": "array", "items": {"type": "object"}},
                            "feedback": {"type": "array", "items": {"type": "object"}},
                            "test_results": {"type": "array", "items": {"type": "object"}},
                            "artifacts": {"type": "array", "items": {"type": "object"}},
                        },
                        "required": [],
                        "additionalProperties": False,
                    },
                ),
                handler=lambda arguments: self._handle_record_updates(arguments),
            ),
            RegisteredTool(
                definition=ToolDefinition(
                    key=MISSION_CREATE_CHECKPOINT,
                    name="create_checkpoint",
                    description="Create a checkpoint snapshot of the current mission artifact with resume instructions.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "checkpoint_name": {"type": "string"},
                            "resume_instructions": {"type": "string"},
                        },
                        "required": ["checkpoint_name", "resume_instructions"],
                        "additionalProperties": False,
                    },
                ),
                handler=lambda arguments: self._handle_create_checkpoint(arguments),
            ),
        )

    def _initialize_artifact(self) -> dict[str, Any]:
        definition = self._definition_stage.run(
            mission_goal=self._config.mission_goal,
            mission_type=self._config.mission_type,
            additional_prompt=self._config.additional_prompt,
        )
        task_plan = self._task_plan_stage.run(definition=definition)
        mission = {
            "definition": definition.to_dict(),
            "mission_status": "active",
            "next_actions": [],
        }
        status_payload = self._status_stage.run(mission=mission, task_plan=task_plan)
        mission["mission_status"] = str(status_payload.get("mission_status", "active"))
        mission["next_actions"] = self._coerce_string_list(status_payload.get("next_actions", []))
        task_plan = MissionTaskPlan(
            tasks=task_plan.tasks,
            current_task_pointer=str(status_payload.get("current_task_pointer") or task_plan.current_task_pointer or ""),
            last_updated=task_plan.last_updated or utc_now_z(),
        )
        task_plan = MissionTaskPlan(
            tasks=task_plan.tasks,
            current_task_pointer=task_plan.current_task_pointer or self._first_open_task_id(task_plan.tasks),
            last_updated=task_plan.last_updated,
        )
        narrative = self._narrative_stage.run(
            mission=mission,
            task_plan=task_plan,
            snapshot=self._memory_store.build_state_snapshot(),
        )
        self._memory_store.initialize_artifact(
            definition=definition,
            task_plan=task_plan,
            narrative=narrative,
            session_id=self.instance_id,
            next_actions=self._coerce_string_list(mission["next_actions"]),
        )
        return self._memory_store.build_state_snapshot()

    def _handle_initialize_artifact(self, arguments: dict[str, Any]) -> dict[str, Any]:
        del arguments
        if self._memory_store.is_initialized():
            return self._memory_store.build_state_snapshot()
        snapshot = self._initialize_artifact()
        self.refresh_parameters()
        self._sync_file_manifest()
        return snapshot

    def _handle_record_updates(self, arguments: dict[str, Any]) -> dict[str, Any]:
        task_updates = self._coerce_mapping_list(arguments.get("task_updates", []))
        progress_events = self._coerce_mapping_list(arguments.get("progress_events", []))
        memory_facts = self._coerce_mapping_list(arguments.get("memory_facts", []))
        decisions = self._coerce_mapping_list(arguments.get("decisions", []))
        errors = self._coerce_mapping_list(arguments.get("errors", []))
        feedback = self._coerce_mapping_list(arguments.get("feedback", []))
        test_results = self._coerce_mapping_list(arguments.get("test_results", []))
        artifacts = self._coerce_mapping_list(arguments.get("artifacts", []))

        for event in progress_events:
            self._memory_store.append_progress_event(event)

        current_plan = self._memory_store.read_task_plan()
        updated_plan = self._apply_task_updates(current_plan, task_updates)
        self._memory_store.write_task_plan(updated_plan)

        if memory_facts:
            self._memory_store.append_memory_facts(memory_facts)
        if decisions:
            self._memory_store.append_decisions(decisions)
        if errors:
            self._memory_store.append_error_records(errors)
        if feedback:
            self._memory_store.append_feedback_records(feedback)
        if test_results:
            self._memory_store.append_test_results(test_results)
        if artifacts:
            self._memory_store.append_artifact_records(artifacts)

        mission = self._memory_store.read_mission()
        status_payload = self._status_stage.run(mission=mission, task_plan=updated_plan)
        reconciled_plan = MissionTaskPlan(
            tasks=updated_plan.tasks,
            current_task_pointer=str(
                status_payload.get("current_task_pointer") or updated_plan.current_task_pointer or ""
            ),
            last_updated=utc_now_z(),
        )
        self._memory_store.write_task_plan(reconciled_plan)
        self._memory_store.update_mission_status(
            str(status_payload.get("mission_status", mission.get("mission_status", "active"))),
            next_actions=self._coerce_string_list(status_payload.get("next_actions", [])),
        )
        narrative = self._narrative_stage.run(
            mission=self._memory_store.read_mission(),
            task_plan=reconciled_plan,
            snapshot=self._memory_store.build_state_snapshot(),
        )
        self._memory_store.write_readme(narrative)
        self._sync_file_manifest()
        self.refresh_parameters()
        return self._memory_store.build_state_snapshot()

    def _handle_create_checkpoint(self, arguments: dict[str, Any]) -> dict[str, Any]:
        checkpoint_name = str(arguments["checkpoint_name"]).strip()
        resume_instructions = str(arguments["resume_instructions"]).strip()
        if not checkpoint_name or not resume_instructions:
            raise ValidationError("checkpoint_name and resume_instructions must not be blank.")
        checkpoint_path = self._memory_store.create_checkpoint(
            checkpoint_name=checkpoint_name,
            resume_instructions=resume_instructions,
        )
        self._memory_store.append_progress_event(
            {
                "timestamp": utc_now_z(),
                "task_id": None,
                "event_type": "checkpoint_created",
                "from_status": None,
                "to_status": None,
                "summary": f"Created checkpoint '{checkpoint_name}'.",
                "session_id": self.instance_id,
            }
        )
        self._sync_file_manifest()
        self.refresh_parameters()
        return {"checkpoint_path": checkpoint_path.as_posix(), **self._memory_store.build_state_snapshot()}

    def _apply_task_updates(self, current_plan: MissionTaskPlan, updates: list[Mapping[str, Any]]) -> MissionTaskPlan:
        task_index = {task.task_id: task for task in current_plan.tasks}
        for update in updates:
            task_id = str(update.get("id", "")).strip()
            if not task_id:
                raise ValidationError("Each task update must include a non-empty 'id'.")
            prior = task_index.get(task_id)
            task_index[task_id] = MissionTask(
                task_id=task_id,
                title=str(update.get("title", prior.title if prior else "")).strip(),
                description=str(update.get("description", prior.description if prior else "")).strip(),
                status=str(update.get("status", prior.status if prior else "pending")),  # type: ignore[arg-type]
                prerequisites=tuple(self._coerce_string_list(update.get("prerequisites", prior.prerequisites if prior else []))),
                complexity=str(update.get("complexity", prior.complexity if prior else "medium")).strip() or "medium",
                assigned_to_session=str(update.get("assigned_to_session", prior.assigned_to_session or self.instance_id)).strip() or None,
                completed_at=str(update.get("completed_at", prior.completed_at or "")).strip() or None,
                blocked_reason=str(update.get("blocked_reason", prior.blocked_reason or "")).strip() or None,
            )
        ordered = tuple(sorted(task_index.values(), key=lambda item: item.task_id))
        return MissionTaskPlan(
            tasks=ordered,
            current_task_pointer=current_plan.current_task_pointer or self._first_open_task_id(ordered),
            last_updated=utc_now_z(),
        )

    def _sync_file_manifest(self) -> None:
        records: list[dict[str, Any]] = []
        for entry in MISSION_DRIVEN_HARNESS_MANIFEST.memory_files:
            path = self.memory_path / entry.relative_path
            records.append(
                {
                    "key": entry.key,
                    "path": path.as_posix(),
                    "exists": path.exists(),
                    "kind": entry.kind,
                    "format": entry.format,
                }
            )
        self._memory_store.write_file_manifest(records)

    def _first_open_task_id(self, tasks: Sequence[MissionTask]) -> str | None:
        for task in tasks:
            if task.status in {"pending", "in_progress", "blocked"}:
                return task.task_id
        return None

    def _coerce_mapping_list(self, value: Any) -> list[Mapping[str, Any]]:
        if not isinstance(value, list):
            raise ValidationError("Expected a list of objects.")
        if not all(isinstance(item, Mapping) for item in value):
            raise ValidationError("Expected a list of objects.")
        return value

    def _coerce_string_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()]


__all__ = ["MissionDrivenAgent"]
