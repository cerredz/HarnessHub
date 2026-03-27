"""Typed model stages for the mission-driven harness."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from harnessiq.agents.helpers import utc_now_z
from harnessiq.agents.subcalls import JsonSubcallRunner, run_json_subcall
from harnessiq.master_prompts import MasterPromptRegistry
from harnessiq.shared.agents import AgentModel, AgentParameterSection, json_parameter_section
from harnessiq.shared.mission_driven import (
    MISSION_DRIVEN_PROMPT_KEY,
    MissionDefinition,
    MissionTaskPlan,
)


@dataclass(frozen=True, slots=True)
class MissionDefinitionStage:
    """Generate the immutable mission definition artifact."""

    model: AgentModel
    runner: JsonSubcallRunner | None = None
    agent_name: str = "mission_driven_agent"

    def run(self, *, mission_goal: str, mission_type: str, additional_prompt: str = "") -> MissionDefinition:
        sections = [
            AgentParameterSection(title="Mission Goal", content=mission_goal),
            AgentParameterSection(title="Mission Type", content=mission_type),
        ]
        if additional_prompt:
            sections.append(AgentParameterSection(title="Additional Instructions", content=additional_prompt))
        payload = run_json_subcall(
            self.model,
            agent_name=self.agent_name,
            system_prompt=(
                f"{self._master_prompt()}\n\n"
                "[STAGE CONTRACT]\n"
                "Generate only the mission definition artifact as JSON. "
                "Return keys: goal, mission_type, success_criteria, scope, constraints, authorization_level, human_contact. "
                "The scope object must contain in_scope and out_of_scope arrays."
            ),
            sections=sections,
            label="mission_definition",
            runner=self.runner,
        )
        return MissionDefinition.from_dict(payload)

    def _master_prompt(self) -> str:
        return MasterPromptRegistry().get_prompt_text(MISSION_DRIVEN_PROMPT_KEY)


@dataclass(frozen=True, slots=True)
class MissionTaskPlanStage:
    """Generate the hierarchical task plan artifact."""

    model: AgentModel
    runner: JsonSubcallRunner | None = None
    agent_name: str = "mission_driven_agent"

    def run(self, *, definition: MissionDefinition) -> MissionTaskPlan:
        payload = run_json_subcall(
            self.model,
            agent_name=self.agent_name,
            system_prompt=(
                f"{self._master_prompt()}\n\n"
                "[STAGE CONTRACT]\n"
                "Generate only the task plan JSON. "
                "Return keys: tasks, current_task_pointer, last_updated. "
                "Each task requires id, title, description, status, prerequisites, complexity, assigned_to_session, completed_at, blocked_reason. "
                "Use pending/in_progress/complete/blocked/skipped only."
            ),
            sections=(json_parameter_section("Mission Definition", definition.to_dict()),),
            label="task_plan",
            runner=self.runner,
        )
        plan = MissionTaskPlan.from_dict(payload)
        if not plan.last_updated:
            plan = MissionTaskPlan(
                tasks=plan.tasks,
                current_task_pointer=plan.current_task_pointer,
                last_updated=utc_now_z(),
            )
        return plan

    def _master_prompt(self) -> str:
        return MasterPromptRegistry().get_prompt_text(MISSION_DRIVEN_PROMPT_KEY)


@dataclass(frozen=True, slots=True)
class MissionStatusStage:
    """Reconcile mission status, next actions, and task pointer from current state."""

    model: AgentModel
    runner: JsonSubcallRunner | None = None
    agent_name: str = "mission_driven_agent"

    def run(self, *, mission: dict[str, Any], task_plan: MissionTaskPlan) -> dict[str, Any]:
        return run_json_subcall(
            self.model,
            agent_name=self.agent_name,
            system_prompt=(
                f"{self._master_prompt()}\n\n"
                "[STAGE CONTRACT]\n"
                "Return only JSON with keys: mission_status, current_task_pointer, next_actions. "
                "mission_status must be one of active, blocked, awaiting_input, paused, complete, failed. "
                "next_actions must be a non-empty array unless the mission is complete."
            ),
            sections=(
                json_parameter_section("Mission", mission),
                json_parameter_section("Task Plan", task_plan.to_dict()),
            ),
            label="mission_status",
            runner=self.runner,
        )

    def _master_prompt(self) -> str:
        return MasterPromptRegistry().get_prompt_text(MISSION_DRIVEN_PROMPT_KEY)


@dataclass(frozen=True, slots=True)
class MissionNarrativeStage:
    """Generate the README narrative from structured mission state."""

    model: AgentModel
    runner: JsonSubcallRunner | None = None
    agent_name: str = "mission_driven_agent"

    def run(self, *, mission: dict[str, Any], task_plan: MissionTaskPlan, snapshot: dict[str, Any]) -> str:
        payload = run_json_subcall(
            self.model,
            agent_name=self.agent_name,
            system_prompt=(
                f"{self._master_prompt()}\n\n"
                "[STAGE CONTRACT]\n"
                "Return only JSON with one key named readme_markdown. "
                "Produce a concise, human-readable README that states the goal, current status, key progress, current work, next actions, and blockers."
            ),
            sections=(
                json_parameter_section("Mission", mission),
                json_parameter_section("Task Plan", task_plan.to_dict()),
                json_parameter_section("Mission Snapshot", snapshot),
            ),
            label="mission_readme",
            runner=self.runner,
        )
        return str(payload.get("readme_markdown", "")).strip()

    def _master_prompt(self) -> str:
        return MasterPromptRegistry().get_prompt_text(MISSION_DRIVEN_PROMPT_KEY)


__all__ = [
    "MissionDefinitionStage",
    "MissionNarrativeStage",
    "MissionStatusStage",
    "MissionTaskPlanStage",
]
