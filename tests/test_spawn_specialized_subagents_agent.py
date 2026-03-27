"""Focused tests for the SpawnSpecializedSubagentsAgent harness."""

from __future__ import annotations

import tempfile
import unittest

from harnessiq.agents import AgentModelRequest, AgentModelResponse, SpawnSpecializedSubagentsAgent
from harnessiq.shared.tools import (
    SPAWN_INTEGRATE_RESULTS,
    SPAWN_PLAN_ASSIGNMENTS,
    SPAWN_RUN_ASSIGNMENT,
)


class _IdleModel:
    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        del request
        return AgentModelResponse(assistant_message="done", should_continue=False)


def _runner(system_prompt, sections, label):  # noqa: ANN001
    del system_prompt, sections
    if label == "delegation_plan":
        return {
            "immediate_local_step": "Review repository entrypoints while workers run.",
            "assignments": [
                {
                    "assignment_id": "worker-1",
                    "title": "Inspect agent exports",
                    "objective": "Confirm public import surface",
                    "owner": "explorer",
                    "deliverable": "Export findings",
                    "completion_condition": "All new harness exports identified",
                    "write_scope": ["harnessiq/agents/__init__.py"],
                    "context_items": ["public exports"],
                }
            ],
            "integration_criteria": ["Integrate only validated results"],
        }
    if label == "worker_worker-1":
        return {
            "assignment_id": "worker-1",
            "status": "completed",
            "summary": "Exports require top-level wiring.",
            "artifact": {"file": "harnessiq/agents/__init__.py", "change": "add exports"},
            "risks": [],
        }
    if label == "integration":
        return {
            "final_response": "Integrated the worker findings into the final plan.",
            "accepted_assignment_ids": ["worker-1"],
            "revised_assignment_ids": [],
            "rejected_assignment_ids": [],
            "follow_up_assignments": [],
        }
    raise AssertionError(label)


class SpawnSpecializedSubagentsAgentTests(unittest.TestCase):
    def test_prepare_creates_initial_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = SpawnSpecializedSubagentsAgent(
                model=_IdleModel(),
                objective="Implement two reusable harnesses",
                available_agent_types=("explorer", "worker"),
                memory_path=temp_dir,
                json_subcall_runner=_runner,
            )

            agent.prepare()

            plan = agent.memory_store.read_plan()
            self.assertEqual(plan["immediate_local_step"], "Review repository entrypoints while workers run.")
            self.assertEqual(len(plan["assignments"]), 1)
            self.assertIn(SPAWN_PLAN_ASSIGNMENTS, {tool.key for tool in agent.available_tools()})

    def test_run_assignment_and_integrate_results_persist_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = SpawnSpecializedSubagentsAgent(
                model=_IdleModel(),
                objective="Implement two reusable harnesses",
                available_agent_types=("explorer", "worker"),
                memory_path=temp_dir,
                json_subcall_runner=_runner,
            )
            agent.prepare()

            worker_result = agent.tool_executor.execute(
                SPAWN_RUN_ASSIGNMENT,
                {"assignment_id": "worker-1"},
            )
            integration = agent.tool_executor.execute(SPAWN_INTEGRATE_RESULTS, {})

            self.assertEqual(worker_result.output["assignment_id"], "worker-1")
            self.assertEqual(len(agent.memory_store.read_worker_outputs()), 1)
            self.assertEqual(integration.output["final_response"], "Integrated the worker findings into the final plan.")
            self.assertIn("Final Response", agent.memory_store.read_readme())


if __name__ == "__main__":
    unittest.main()
