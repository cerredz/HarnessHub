"""Typed model stages for the spawn-specialized-subagents harness."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from harnessiq.agents.subcalls import JsonSubcallRunner, run_json_subcall
from harnessiq.master_prompts import MasterPromptRegistry
from harnessiq.shared.agents import AgentModel, AgentParameterSection, json_parameter_section
from harnessiq.shared.dtos.prompt_harnesses import SubAgentAssignmentDTO, WorkerExecutionResultDTO
from harnessiq.shared.spawn_specialized_subagents import SPAWN_SPECIALIZED_SUBAGENTS_PROMPT_KEY


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
            system_prompt=(
                f"{self._master_prompt()}\n\n"
                "[STAGE CONTRACT]\n"
                "Return only JSON with keys: immediate_local_step, assignments, integration_criteria. "
                "Each assignment must include assignment_id, title, objective, owner, deliverable, completion_condition, write_scope, context_items."
            ),
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

    def _master_prompt(self) -> str:
        return MasterPromptRegistry().get_prompt_text(SPAWN_SPECIALIZED_SUBAGENTS_PROMPT_KEY)


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
            system_prompt=(
                f"{self._master_prompt()}\n\n"
                "[STAGE CONTRACT]\n"
                "Execute exactly one worker assignment. "
                "Return only JSON with keys: assignment_id, status, summary, artifact, risks. "
                "status must be completed or blocked."
            ),
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

    def _master_prompt(self) -> str:
        return MasterPromptRegistry().get_prompt_text(SPAWN_SPECIALIZED_SUBAGENTS_PROMPT_KEY)


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
            system_prompt=(
                f"{self._master_prompt()}\n\n"
                "[STAGE CONTRACT]\n"
                "Return only JSON with keys: final_response, accepted_assignment_ids, revised_assignment_ids, rejected_assignment_ids, follow_up_assignments. "
                "follow_up_assignments must use the same assignment schema as the planner stage."
            ),
            sections=(
                AgentParameterSection(title="Primary Objective", content=objective),
                json_parameter_section("Current Plan", plan),
                json_parameter_section("Worker Outputs", list(worker_outputs)),
            ),
            label="integration",
            runner=self.runner,
        )

    def _master_prompt(self) -> str:
        return MasterPromptRegistry().get_prompt_text(SPAWN_SPECIALIZED_SUBAGENTS_PROMPT_KEY)


__all__ = ["DelegationPlannerStage", "IntegrationStage", "WorkerExecutionStage"]
