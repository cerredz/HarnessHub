"""Focused tests for the MissionDrivenAgent harness."""

from __future__ import annotations

import tempfile
import unittest

from harnessiq.agents import AgentModelRequest, AgentModelResponse, MissionDrivenAgent
from harnessiq.shared.tools import (
    MISSION_CREATE_CHECKPOINT,
    MISSION_INITIALIZE_ARTIFACT,
    MISSION_RECORD_UPDATES,
)


class _IdleModel:
    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        del request
        return AgentModelResponse(assistant_message="done", should_continue=False)


def _runner_factory(*, completion_mode: bool = False):
    status_calls = {"count": 0}

    def runner(system_prompt, sections, label):  # noqa: ANN001
        del system_prompt, sections
        if label == "mission_definition":
            return {
                "goal": "Ship reusable mission orchestration harness",
                "mission_type": "app_build",
                "success_criteria": ["Harness exists", "Artifact persists"],
                "scope": {"in_scope": ["shared contracts", "agent harness"], "out_of_scope": ["CLI"]},
                "constraints": ["Do not lose mission state"],
                "authorization_level": "local code and tests only",
                "human_contact": "repository owner",
            }
        if label == "task_plan":
            return {
                "tasks": [
                    {
                        "id": "1",
                        "title": "Create shared contracts",
                        "description": "Add memory store and manifest",
                        "status": "pending",
                        "prerequisites": [],
                        "complexity": "medium",
                        "assigned_to_session": None,
                        "completed_at": None,
                        "blocked_reason": None,
                    }
                ],
                "current_task_pointer": "1",
                "last_updated": "2026-03-27T00:00:00Z",
            }
        if label == "mission_status":
            status_calls["count"] += 1
            if completion_mode and status_calls["count"] > 1:
                return {
                    "mission_status": "complete",
                    "current_task_pointer": None,
                    "next_actions": [],
                }
            return {
                "mission_status": "active",
                "current_task_pointer": "1",
                "next_actions": ["Start task 1"],
            }
        if label == "mission_readme":
            return {"readme_markdown": "# Mission\n\nCurrent status is tracked.\n"}
        raise AssertionError(label)

    return runner


class MissionDrivenAgentTests(unittest.TestCase):
    def test_prepare_initializes_full_artifact_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = MissionDrivenAgent(
                model=_IdleModel(),
                mission_goal="Ship reusable mission orchestration harness",
                mission_type="app_build",
                memory_path=temp_dir,
                json_subcall_runner=_runner_factory(),
            )

            agent.prepare()

            self.assertTrue((agent.memory_path / "mission.json").exists())
            self.assertTrue((agent.memory_path / "task_plan.json").exists())
            self.assertTrue((agent.memory_path / "progress_log.jsonl").exists())
            self.assertTrue((agent.memory_path / "README.md").exists())
            self.assertEqual(agent.build_ledger_outputs()["mission_status"], "active")
            self.assertIn(MISSION_INITIALIZE_ARTIFACT, {tool.key for tool in agent.available_tools()})
            self.assertIn(MISSION_RECORD_UPDATES, {tool.key for tool in agent.available_tools()})

    def test_record_updates_persists_task_and_log_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = MissionDrivenAgent(
                model=_IdleModel(),
                mission_goal="Ship reusable mission orchestration harness",
                mission_type="app_build",
                memory_path=temp_dir,
                json_subcall_runner=_runner_factory(completion_mode=True),
            )
            agent.prepare()

            result = agent.tool_executor.execute(
                MISSION_RECORD_UPDATES,
                {
                    "task_updates": [
                        {
                            "id": "1",
                            "title": "Create shared contracts",
                            "description": "Add memory store and manifest",
                            "status": "complete",
                            "completed_at": "2026-03-27T01:00:00Z",
                        }
                    ],
                    "progress_events": [
                        {
                            "timestamp": "2026-03-27T01:00:00Z",
                            "task_id": "1",
                            "event_type": "task_completed",
                            "from_status": "in_progress",
                            "to_status": "complete",
                            "summary": "Completed task 1.",
                            "session_id": "session-1",
                        }
                    ],
                    "memory_facts": [{"key": "pattern", "value": "use manifests", "confidence": "confirmed"}],
                },
            )

            self.assertEqual(result.output["mission_status"], "complete")
            self.assertEqual(agent.memory_store.read_task_plan().tasks[0].status, "complete")
            self.assertEqual(len(agent.memory_store.read_memory_facts()), 1)
            self.assertIn("Mission", agent.memory_store.read_readme())

    def test_create_checkpoint_writes_snapshot_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = MissionDrivenAgent(
                model=_IdleModel(),
                mission_goal="Ship reusable mission orchestration harness",
                mission_type="app_build",
                memory_path=temp_dir,
                json_subcall_runner=_runner_factory(),
            )
            agent.prepare()

            result = agent.tool_executor.execute(
                MISSION_CREATE_CHECKPOINT,
                {
                    "checkpoint_name": "before_merge",
                    "resume_instructions": "Resume from the current task plan and validate state.",
                },
            )

            self.assertIn("checkpoint_path", result.output)
            self.assertTrue(agent.memory_path.joinpath("checkpoints").exists())


if __name__ == "__main__":
    unittest.main()
