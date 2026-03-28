"""Concrete spawn-specialized-subagents harness implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from harnessiq.agents.base import BaseAgent
from harnessiq.agents.helpers import resolve_memory_path, utc_now_z
from harnessiq.agents.sdk_helpers import merge_profile_parameters, resolve_profile_memory_path
from harnessiq.agents.spawn_specialized_subagents.stages import (
    DelegationPlannerStage,
    IntegrationStage,
    WorkerExecutionStage,
)
from harnessiq.config import HarnessProfile
from harnessiq.agents.subcalls import JsonSubcallRunner
from harnessiq.shared.agents import (
    AgentModel,
    AgentParameterSection,
    AgentRuntimeConfig,
    json_parameter_section,
    merge_agent_runtime_config,
)
from harnessiq.shared.dtos.prompt_harnesses import (
    SpawnSpecializedSubagentsInstancePayload,
    SubAgentAssignmentDTO,
)
from harnessiq.shared.exceptions import ValidationError
from harnessiq.shared.spawn_specialized_subagents import (
    DEFAULT_SPAWN_SUBAGENTS_RESET_THRESHOLD,
    SPAWN_SPECIALIZED_SUBAGENTS_HARNESS_MANIFEST,
    SpawnSpecializedSubagentsConfig,
    SpawnSpecializedSubagentsMemoryStore,
    normalize_spawn_subagents_custom_parameters,
    normalize_spawn_subagents_runtime_parameters,
)
from harnessiq.shared.tools import (
    RegisteredTool,
)
from harnessiq.tools.spawn_specialized_subagents import create_spawn_specialized_subagents_tools
from harnessiq.tools.registry import create_tool_registry

_DEFAULT_MEMORY_PATH = Path(SPAWN_SPECIALIZED_SUBAGENTS_HARNESS_MANIFEST.resolved_default_memory_root)


class SpawnSpecializedSubagentsAgent(BaseAgent):
    """Reusable delegation-orchestration harness built from the bundled master prompt."""

    def __init__(
        self,
        *,
        model: AgentModel,
        objective: str,
        available_agent_types: Sequence[str] = (),
        current_context: str = "",
        memory_path: str | Path | None = None,
        additional_prompt: str = "",
        max_tokens: int = 80_000,
        reset_threshold: float = DEFAULT_SPAWN_SUBAGENTS_RESET_THRESHOLD,
        tools: Sequence[RegisteredTool] | None = None,
        runtime_config: AgentRuntimeConfig | None = None,
        json_subcall_runner: JsonSubcallRunner | None = None,
        instance_name: str | None = None,
    ) -> None:
        resolved_memory_path = resolve_memory_path(memory_path, default_path=_DEFAULT_MEMORY_PATH)
        self._config = SpawnSpecializedSubagentsConfig(
            memory_path=resolved_memory_path,
            objective=objective,
            available_agent_types=tuple(str(item) for item in available_agent_types),
            current_context=current_context,
            additional_prompt=additional_prompt,
            max_tokens=max_tokens,
            reset_threshold=reset_threshold,
        )
        self._json_subcall_runner = json_subcall_runner
        tool_registry = create_tool_registry(
            create_spawn_specialized_subagents_tools(
                plan_assignments_handler=self._handle_plan_assignments,
                run_assignment_handler=self._handle_run_assignment,
                integrate_results_handler=self._handle_integrate_results,
            ),
            tuple(tools or ()),
        )
        super().__init__(
            name="spawn_specialized_subagents_agent",
            model=model,
            tool_executor=tool_registry,
            runtime_config=merge_agent_runtime_config(
                runtime_config,
                max_tokens=max_tokens,
                reset_threshold=reset_threshold,
            ),
            memory_path=resolved_memory_path,
            instance_name=instance_name,
        )
        self._config = SpawnSpecializedSubagentsConfig(
            memory_path=self.memory_path,
            objective=objective,
            available_agent_types=tuple(str(item) for item in available_agent_types),
            current_context=current_context,
            additional_prompt=additional_prompt,
            max_tokens=max_tokens,
            reset_threshold=reset_threshold,
        )
        self._memory_store = self._create_file_backed_store(
            store_factory=SpawnSpecializedSubagentsMemoryStore,
            runtime_parameters=self._runtime_parameters_payload(),
            custom_parameters=self._custom_parameters_payload(),
            additional_prompt=self._config.additional_prompt,
            sync_callback=self._sync_spawn_state,
        )
        self._planner_stage = DelegationPlannerStage(model=model, runner=json_subcall_runner, agent_name=self.name)
        self._worker_stage = WorkerExecutionStage(model=model, runner=json_subcall_runner, agent_name=self.name)
        self._integration_stage = IntegrationStage(model=model, runner=json_subcall_runner, agent_name=self.name)

    @property
    def config(self) -> SpawnSpecializedSubagentsConfig:
        return self._config

    @property
    def memory_store(self) -> SpawnSpecializedSubagentsMemoryStore:
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
    ) -> "SpawnSpecializedSubagentsAgent":
        resolved_memory_path = resolve_memory_path(memory_path, default_path=_DEFAULT_MEMORY_PATH)
        store = SpawnSpecializedSubagentsMemoryStore(memory_path=resolved_memory_path)
        store.prepare()
        runtime_parameters = store.read_runtime_parameters()
        if runtime_overrides:
            runtime_parameters.update(runtime_overrides)
        custom_parameters = store.read_custom_parameters()
        if custom_overrides:
            custom_parameters.update(custom_overrides)
        normalized_runtime = normalize_spawn_subagents_runtime_parameters(runtime_parameters)
        normalized_custom = normalize_spawn_subagents_custom_parameters(custom_parameters)
        available_agent_types = [
            item.strip()
            for item in str(normalized_custom.get("available_agent_types", "")).split(",")
            if item.strip()
        ]
        return cls(
            model=model,
            memory_path=resolved_memory_path,
            objective=str(normalized_custom["objective"]),
            available_agent_types=available_agent_types,
            current_context=store.read_current_context(),
            additional_prompt=store.read_additional_prompt(),
            tools=tools,
            runtime_config=runtime_config,
            json_subcall_runner=json_subcall_runner,
            instance_name=instance_name,
            **normalized_runtime,
        )

    @classmethod
    def from_profile(
        cls,
        *,
        profile: HarnessProfile,
        model: AgentModel,
        memory_path: str | Path | None = None,
        tools: Sequence[RegisteredTool] | None = None,
        runtime_config: AgentRuntimeConfig | None = None,
        runtime_overrides: Mapping[str, Any] | None = None,
        custom_overrides: Mapping[str, Any] | None = None,
        json_subcall_runner: JsonSubcallRunner | None = None,
        instance_name: str | None = None,
    ) -> "SpawnSpecializedSubagentsAgent":
        resolved_path = resolve_profile_memory_path(
            profile=profile,
            manifest=SPAWN_SPECIALIZED_SUBAGENTS_HARNESS_MANIFEST,
            memory_path=memory_path,
        )
        resolved_runtime, resolved_custom = merge_profile_parameters(
            profile=profile,
            runtime_overrides=runtime_overrides,
            custom_overrides=custom_overrides,
        )
        return cls.from_memory(
            model=model,
            memory_path=resolved_path,
            runtime_overrides=resolved_runtime,
            custom_overrides=resolved_custom,
            tools=tools,
            runtime_config=runtime_config,
            json_subcall_runner=json_subcall_runner,
            instance_name=instance_name or profile.agent_name,
        )

    def build_instance_payload(self) -> dict[str, Any]:
        return SpawnSpecializedSubagentsInstancePayload(
            memory_path=self._config.memory_path,
            objective=self._config.objective,
            available_agent_types=self._config.available_agent_types,
            current_context=self._config.current_context,
            additional_prompt=self._config.additional_prompt,
            max_tokens=self._config.max_tokens,
            reset_threshold=self._config.reset_threshold,
        ).to_dict()

    def prepare(self) -> None:
        self._sync_file_backed_store(
            self._memory_store,
            runtime_parameters=self._runtime_parameters_payload(),
            custom_parameters=self._custom_parameters_payload(),
            additional_prompt=self._config.additional_prompt,
            sync_callback=self._sync_spawn_state,
        )
        if not self._memory_store.read_plan().get("assignments"):
            self._plan_assignments()
        self._memory_store.write_readme(self._render_readme())

    def build_system_prompt(self) -> str:
        return (
            "You are SpawnSpecializedSubagentsAgent. "
            "Plan bounded delegation, execute assignments one at a time through tools, and integrate results into a single coherent outcome."
        )

    def load_parameter_sections(self) -> Sequence[AgentParameterSection]:
        return (
            AgentParameterSection(title="Planner Stage Prompt", content=self._planner_stage.system_prompt()),
            AgentParameterSection(title="Objective", content=self._memory_store.read_objective()),
            AgentParameterSection(
                title="Current Context",
                content=self._memory_store.read_current_context() or "(no current context)",
            ),
            json_parameter_section("Orchestration Plan", self._memory_store.read_plan()),
            json_parameter_section("Worker Outputs", self._memory_store.read_worker_outputs()),
            json_parameter_section("Integration Summary", self._memory_store.read_integration_summary()),
        )

    def build_ledger_outputs(self) -> dict[str, Any]:
        snapshot = self._memory_store.build_state_snapshot()
        snapshot["final_response"] = self._memory_store.read_integration_summary().get("final_response")
        return snapshot

    def build_ledger_tags(self) -> list[str]:
        return ["delegation", "orchestration", "subagents"]

    def _runtime_parameters_payload(self) -> dict[str, Any]:
        return {
            "max_tokens": self._config.max_tokens,
            "reset_threshold": self._config.reset_threshold,
        }

    def _custom_parameters_payload(self) -> dict[str, Any]:
        return {
            "objective": self._config.objective,
            "available_agent_types": ",".join(self._config.available_agent_types),
        }

    def _sync_spawn_state(self, store: SpawnSpecializedSubagentsMemoryStore) -> None:
        store.write_objective(self._config.objective)
        store.write_current_context(self._config.current_context)

    def _plan_assignments(self) -> dict[str, Any]:
        payload = self._planner_stage.run(
            objective=self._memory_store.read_objective(),
            available_agent_types=self._config.available_agent_types,
            current_context=self._memory_store.read_current_context(),
            prior_worker_outputs=self._memory_store.read_worker_outputs(),
            additional_prompt=self._memory_store.read_additional_prompt(),
        )
        assignments = payload["assignments"]
        self._memory_store.write_plan(
            immediate_local_step=payload["immediate_local_step"],
            assignments=assignments,
            integration_criteria=payload["integration_criteria"],
        )
        self._memory_store.append_execution_log(
            {
                "timestamp": utc_now_z(),
                "event_type": "plan_refreshed",
                "assignment_count": len(assignments),
            }
        )
        self._memory_store.write_readme(self._render_readme())
        return self._memory_store.read_plan()

    def _handle_plan_assignments(self, arguments: dict[str, Any]) -> dict[str, Any]:
        del arguments
        payload = self._plan_assignments()
        self.refresh_parameters()
        return payload

    def _handle_run_assignment(self, arguments: dict[str, Any]) -> dict[str, Any]:
        assignment_id = str(arguments["assignment_id"]).strip()
        if not assignment_id:
            raise ValidationError("assignment_id must not be blank.")
        plan = self._memory_store.read_plan()
        assignment = self._find_assignment(plan, assignment_id)
        result = self._worker_stage.run(
            objective=self._memory_store.read_objective(),
            assignment=assignment,
            current_context=self._memory_store.read_current_context(),
            prior_outputs=self._memory_store.read_worker_outputs(),
        )
        self._memory_store.append_worker_output(result.to_dict())
        self._memory_store.append_execution_log(
            {
                "timestamp": utc_now_z(),
                "event_type": "assignment_executed",
                "assignment_id": result.assignment_id,
                "status": result.status,
            }
        )
        self._memory_store.write_readme(self._render_readme())
        self.refresh_parameters()
        return result.to_dict()

    def _handle_integrate_results(self, arguments: dict[str, Any]) -> dict[str, Any]:
        del arguments
        plan = self._memory_store.read_plan()
        worker_outputs = self._memory_store.read_worker_outputs()
        if not worker_outputs:
            raise ValidationError("Cannot integrate results before at least one worker output exists.")
        payload = self._integration_stage.run(
            objective=self._memory_store.read_objective(),
            plan=plan,
            worker_outputs=worker_outputs,
        )
        self._memory_store.write_integration_summary(payload)
        self._memory_store.append_execution_log(
            {
                "timestamp": utc_now_z(),
                "event_type": "results_integrated",
                "accepted_assignment_ids": payload.get("accepted_assignment_ids", []),
            }
        )
        self._memory_store.write_readme(self._render_readme())
        self.refresh_parameters()
        return payload

    def _find_assignment(self, plan: Mapping[str, Any], assignment_id: str) -> SubAgentAssignmentDTO:
        raw_assignments = plan.get("assignments", [])
        if not isinstance(raw_assignments, list):
            raise ValidationError("Current plan does not contain assignments.")
        for item in raw_assignments:
            if not isinstance(item, Mapping):
                continue
            if str(item.get("assignment_id", "")).strip() != assignment_id:
                continue
            return SubAgentAssignmentDTO(
                assignment_id=assignment_id,
                title=str(item.get("title", "")).strip(),
                objective=str(item.get("objective", "")).strip(),
                owner=str(item.get("owner", "")).strip(),
                deliverable=str(item.get("deliverable", "")).strip(),
                completion_condition=str(item.get("completion_condition", "")).strip(),
                write_scope=tuple(str(value).strip() for value in item.get("write_scope", []) if str(value).strip()),
                context_items=tuple(str(value).strip() for value in item.get("context_items", []) if str(value).strip()),
            )
        raise ValidationError(f"No assignment with id '{assignment_id}' exists in the current plan.")

    def _render_readme(self) -> str:
        snapshot = self._memory_store.build_state_snapshot()
        final_response = self._memory_store.read_integration_summary().get("final_response")
        lines = [
            "# Spawn Specialized Subagents",
            "",
            f"Objective: {self._memory_store.read_objective()}",
            f"Immediate Local Step: {snapshot.get('immediate_local_step') or '(not planned)'}",
            f"Assignments: {snapshot.get('assignment_count', 0)}",
            f"Worker Outputs: {snapshot.get('worker_output_count', 0)}",
        ]
        if final_response:
            lines.extend(["", "## Final Response", "", str(final_response)])
        return "\n".join(lines).rstrip() + "\n"


__all__ = ["SpawnSpecializedSubagentsAgent"]
