"""
===============================================================================
File: harnessiq/agents/mission_driven/stages.py

What this file does:
- Defines the staged sub-workflows used by the `mission_driven` agent package.
- Typed model stages for the mission-driven harness.

Use cases:
- Use these stage helpers when the agent needs explicit subcalls or
  deterministic planning steps before or after the main loop.

How to use it:
- Instantiate the stage objects from the sibling agent runtime and feed them
  the domain payloads they expect.

Intent:
- Separate reusable stage logic from the top-level agent class so multi-step
  workflows stay testable and easier to reason about.
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from harnessiq.agents.helpers import utc_now_z
from harnessiq.agents.subcalls import JsonSubcallRunner, run_json_subcall
from harnessiq.shared.agents import AgentModel, AgentParameterSection, json_parameter_section
from harnessiq.shared.mission_driven import MissionDefinition, MissionTaskPlan


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
            system_prompt=self.system_prompt(),
            sections=sections,
            label="mission_definition",
            runner=self.runner,
        )
        return MissionDefinition.from_dict(payload)

    def system_prompt(self) -> str:
        return (
            "You are the mission definition author for MissionDrivenAgent.\n"
            "Your only job is to write the immutable mission definition artifact that anchors scope and authority.\n"
            "Translate the provided mission goal and mission type into a precise contract with success criteria, "
            "explicit in-scope and out-of-scope boundaries, operating constraints, authorization level, and human contact.\n"
            "Do not create tasks, status updates, progress history, or README prose.\n"
            "Return only JSON with keys: goal, mission_type, success_criteria, scope, constraints, authorization_level, human_contact.\n"
            "The scope object must contain in_scope and out_of_scope arrays."
        )


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
            system_prompt=self.system_prompt(),
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

    def system_prompt(self) -> str:
        return (
            "You are the task-plan decomposer for MissionDrivenAgent.\n"
            "Break the mission definition into a concrete, dependency-aware execution plan that a cold-start agent can follow without guessing.\n"
            "Produce only the task hierarchy, task metadata, and current task pointer. Do not write narrative summaries or decision rationale.\n"
            "Return only JSON with keys: tasks, current_task_pointer, last_updated.\n"
            "Each task must include id, title, description, status, prerequisites, complexity, assigned_to_session, completed_at, blocked_reason.\n"
            "Use only these statuses: pending, in_progress, complete, blocked, skipped."
        )


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
            system_prompt=self.system_prompt(),
            sections=(
                json_parameter_section("Mission", mission),
                json_parameter_section("Task Plan", task_plan.to_dict()),
            ),
            label="mission_status",
            runner=self.runner,
        )

    def system_prompt(self) -> str:
        return (
            "You are the mission status reconciler for MissionDrivenAgent.\n"
            "Inspect the current mission record and task plan, then determine the aggregate mission status, "
            "the correct current task pointer, and the next executable action queue.\n"
            "Favor explicit, operational next actions over vague summaries.\n"
            "Return only JSON with keys: mission_status, current_task_pointer, next_actions.\n"
            "mission_status must be one of active, blocked, awaiting_input, paused, complete, failed.\n"
            "next_actions must be a non-empty array unless the mission is complete."
        )


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
            system_prompt=self.system_prompt(),
            sections=(
                json_parameter_section("Mission", mission),
                json_parameter_section("Task Plan", task_plan.to_dict()),
                json_parameter_section("Mission Snapshot", snapshot),
            ),
            label="mission_readme",
            runner=self.runner,
        )
        return str(payload.get("readme_markdown", "")).strip()

    def system_prompt(self) -> str:
        return (
            "You are the narrative summarizer for MissionDrivenAgent.\n"
            "Translate the structured mission state into a concise, operator-facing README that a new engineer can skim to orient quickly.\n"
            "Summarize the goal, current status, progress, current work, next actions, blockers, and the most important durable findings.\n"
            "Do not invent state that is not present in the structured inputs.\n"
            "Return only JSON with one key named readme_markdown."
        )


__all__ = [
    "MissionDefinitionStage",
    "MissionNarrativeStage",
    "MissionStatusStage",
    "MissionTaskPlanStage",
]
