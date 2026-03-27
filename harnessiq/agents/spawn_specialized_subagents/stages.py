"""Typed model stages for the spawn-specialized-subagents harness."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from harnessiq.agents.subcalls import JsonSubcallRunner, run_json_subcall
from harnessiq.shared.agents import AgentModel, AgentParameterSection, json_parameter_section
from harnessiq.shared.dtos.prompt_harnesses import SubAgentAssignmentDTO, WorkerExecutionResultDTO


@dataclass(frozen=True, slots=True)
class DelegationPlannerStage:
    """Create the current local step and bounded worker assignments."""

    model: AgentModel
    runner: JsonSubcallRunner | None = None
    agent_name: str = "spawn_specialized_subagents_agent"

    def run(
        self,
        *,
        objective: str,
        available_agent_types: Sequence[str],
        current_context: str,
        prior_worker_outputs: Sequence[dict[str, Any]],
        additional_prompt: str = "",
    ) -> dict[str, Any]:
        sections = [
            AgentParameterSection(title="Primary Objective", content=objective),
            json_parameter_section("Available Agent Types", list(available_agent_types)),
            AgentParameterSection(title="Current Context", content=current_context or "(none)"),
            json_parameter_section("Prior Worker Outputs", list(prior_worker_outputs)),
        ]
        if additional_prompt:
            sections.append(AgentParameterSection(title="Additional Instructions", content=additional_prompt))
        payload = run_json_subcall(
            self.model,
            agent_name=self.agent_name,
            system_prompt=self.system_prompt(),
            sections=sections,
            label="delegation_plan",
            runner=self.runner,
        )
        assignments = [
            SubAgentAssignmentDTO(
                assignment_id=str(item.get("assignment_id", "")).strip(),
                title=str(item.get("title", "")).strip(),
                objective=str(item.get("objective", "")).strip(),
                owner=str(item.get("owner", "")).strip(),
                deliverable=str(item.get("deliverable", "")).strip(),
                completion_condition=str(item.get("completion_condition", "")).strip(),
                write_scope=tuple(str(value).strip() for value in item.get("write_scope", []) if str(value).strip()),
                context_items=tuple(str(value).strip() for value in item.get("context_items", []) if str(value).strip()),
            )
            for item in payload.get("assignments", [])
            if isinstance(item, dict)
        ]
        return {
            "immediate_local_step": str(payload.get("immediate_local_step", "")).strip(),
            "assignments": assignments,
            "integration_criteria": [
                str(item).strip()
                for item in payload.get("integration_criteria", [])
                if str(item).strip()
            ],
        }

    def system_prompt(self) -> str:
        return (
            "You are the delegation planner for SpawnSpecializedSubagentsAgent.\n"
            "Decide the immediate local step and a bounded set of worker assignments that advance the objective without overlapping ownership.\n"
            "Assignments must be concrete, reviewable, and integration-ready.\n"
            "Return only JSON with keys: immediate_local_step, assignments, integration_criteria.\n"
            "Each assignment must include assignment_id, title, objective, owner, deliverable, completion_condition, write_scope, context_items."
        )


@dataclass(frozen=True, slots=True)
class WorkerExecutionStage:
    """Execute one bounded worker assignment as a typed subcall."""

    model: AgentModel
    runner: JsonSubcallRunner | None = None
    agent_name: str = "spawn_specialized_subagents_agent"

    def run(
        self,
        *,
        objective: str,
        assignment: SubAgentAssignmentDTO,
        current_context: str,
        prior_outputs: Sequence[dict[str, Any]],
    ) -> WorkerExecutionResultDTO:
        payload = run_json_subcall(
            self.model,
            agent_name=self.agent_name,
            system_prompt=self.system_prompt(),
            sections=(
                AgentParameterSection(title="Primary Objective", content=objective),
                json_parameter_section("Assignment", assignment.to_dict()),
                AgentParameterSection(title="Current Context", content=current_context or "(none)"),
                json_parameter_section("Prior Worker Outputs", list(prior_outputs)),
            ),
            label=f"worker_{assignment.assignment_id}",
            runner=self.runner,
        )
        return WorkerExecutionResultDTO(
            assignment_id=str(payload.get("assignment_id", assignment.assignment_id)).strip() or assignment.assignment_id,
            status=str(payload.get("status", "completed")).strip() or "completed",
            summary=str(payload.get("summary", "")).strip(),
            artifact=dict(payload.get("artifact", {})) if isinstance(payload.get("artifact", {}), dict) else {},
            risks=tuple(str(item).strip() for item in payload.get("risks", []) if str(item).strip()),
        )

    def system_prompt(self) -> str:
        return (
            "You are the worker-execution stage for SpawnSpecializedSubagentsAgent.\n"
            "Execute exactly one bounded assignment, stay within the assigned scope, and return a crisp structured result.\n"
            "Do not replan the entire objective or invent extra work outside the assignment contract.\n"
            "Return only JSON with keys: assignment_id, status, summary, artifact, risks.\n"
            "status must be completed or blocked."
        )


@dataclass(frozen=True, slots=True)
class IntegrationStage:
    """Integrate worker outputs into one coherent orchestration result."""

    model: AgentModel
    runner: JsonSubcallRunner | None = None
    agent_name: str = "spawn_specialized_subagents_agent"

    def run(
        self,
        *,
        objective: str,
        plan: dict[str, Any],
        worker_outputs: Sequence[dict[str, Any]],
    ) -> dict[str, Any]:
        return run_json_subcall(
            self.model,
            agent_name=self.agent_name,
            system_prompt=self.system_prompt(),
            sections=(
                AgentParameterSection(title="Primary Objective", content=objective),
                json_parameter_section("Current Plan", plan),
                json_parameter_section("Worker Outputs", list(worker_outputs)),
            ),
            label="integration",
            runner=self.runner,
        )

    def system_prompt(self) -> str:
        return (
            "You are the integration stage for SpawnSpecializedSubagentsAgent.\n"
            "Review worker outputs against the objective and plan, then integrate the useful work into one coherent response.\n"
            "Be explicit about what was accepted, revised, rejected, and what follow-up work remains.\n"
            "Return only JSON with keys: final_response, accepted_assignment_ids, revised_assignment_ids, rejected_assignment_ids, follow_up_assignments.\n"
            "follow_up_assignments must use the same assignment schema as the planner stage."
        )


__all__ = ["DelegationPlannerStage", "IntegrationStage", "WorkerExecutionStage"]
