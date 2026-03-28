"""Focused tests for the MissionDrivenAgent harness."""

from __future__ import annotations

import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

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


@contextmanager
def _isolated_repo():
    original_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        try:
            os.mkdir(".git")
            yield Path(temp_dir)
        finally:
            os.chdir(original_cwd)


class MissionDrivenAgentTests(unittest.TestCase):
    def test_prepare_initializes_full_artifact_layout(self) -> None:
        with _isolated_repo() as repo_root:
            agent = MissionDrivenAgent(
                model=_IdleModel(),
                mission_goal="Ship reusable mission orchestration harness",
                mission_type="app_build",
                memory_path=repo_root / "agent-memory",
                json_subcall_runner=_runner_factory(),
            )

            agent.prepare()

            self.assertTrue((agent.memory_path / "mission.json").exists())
            self.assertTrue((agent.memory_path / "task_plan.json").exists())
            self.assertTrue((agent.memory_path / "tool_call_history.json").exists())
            self.assertTrue((agent.memory_path / "research_log.json").exists())
            self.assertTrue((agent.memory_path / "next_actions.json").exists())
            self.assertTrue((agent.memory_path / "mission_status.json").exists())
            self.assertTrue((agent.memory_path / "progress_log.jsonl").exists())
            self.assertTrue((agent.memory_path / "README.md").exists())
            self.assertEqual(agent.build_ledger_outputs()["mission_status"], "active")
            self.assertIn(MISSION_INITIALIZE_ARTIFACT, {tool.key for tool in agent.available_tools()})
            self.assertIn(MISSION_RECORD_UPDATES, {tool.key for tool in agent.available_tools()})

    def test_record_updates_persists_task_and_log_changes(self) -> None:
        with _isolated_repo() as repo_root:
            agent = MissionDrivenAgent(
                model=_IdleModel(),
                mission_goal="Ship reusable mission orchestration harness",
                mission_type="app_build",
                memory_path=repo_root / "agent-memory",
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
                    "decisions": [
                        {
                            "decision": "Use manifests",
                            "rationale": "Keeps agent wiring consistent.",
                            "rejected_alternatives": ["Hard-code parameters per agent"],
                        }
                    ],
                    "file_records": [
                        {
                            "path": "harnessiq/agents/mission_driven/agent.py",
                            "purpose": "Mission harness orchestration.",
                            "dependencies": ["harnessiq/shared/mission_driven.py"],
                        }
                    ],
                    "research_entries": [
                        {
                            "source": "PR #382 review",
                            "summary": "Review requires richer durable records.",
                        }
                    ],
                },
            )

            self.assertEqual(result.output["mission_status"], "complete")
            self.assertEqual(agent.memory_store.read_task_plan().tasks[0].status, "complete")
            self.assertEqual(len(agent.memory_store.read_memory_facts()), 1)
            self.assertEqual(len(agent.memory_store.read_research_records()), 1)
            self.assertGreaterEqual(len(agent.memory_store.read_tool_call_records()), 2)
            self.assertGreaterEqual(len(agent.memory_store.read_file_manifest()), 19)
            self.assertIn("Mission", agent.memory_store.read_readme())

    def test_create_checkpoint_writes_snapshot_file(self) -> None:
        with _isolated_repo() as repo_root:
            agent = MissionDrivenAgent(
                model=_IdleModel(),
                mission_goal="Ship reusable mission orchestration harness",
                mission_type="app_build",
                memory_path=repo_root / "agent-memory",
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
            self.assertGreaterEqual(len(agent.memory_store.read_tool_call_records()), 2)

    def test_record_updates_can_explicitly_clear_next_actions(self) -> None:
        with _isolated_repo() as repo_root:
            agent = MissionDrivenAgent(
                model=_IdleModel(),
                mission_goal="Ship reusable mission orchestration harness",
                mission_type="app_build",
                memory_path=repo_root / "agent-memory",
                json_subcall_runner=_runner_factory(),
            )
            agent.prepare()

            result = agent.tool_executor.execute(
                MISSION_RECORD_UPDATES,
                {
                    "next_actions": [],
                },
            )

            self.assertEqual(result.output["next_actions"], [])
            self.assertEqual(agent.memory_store.read_next_actions(), [])

    def test_default_memory_path_creates_isolated_subfolders(self) -> None:
        with _isolated_repo():
            first = MissionDrivenAgent(
                model=_IdleModel(),
                mission_goal="Ship reusable mission orchestration harness",
                mission_type="app_build",
                json_subcall_runner=_runner_factory(),
            )
            second = MissionDrivenAgent(
                model=_IdleModel(),
                mission_goal="Ship reusable mission orchestration harness",
                mission_type="app_build",
                json_subcall_runner=_runner_factory(),
            )

        self.assertNotEqual(first.memory_path, second.memory_path)
        self.assertEqual(first.memory_path.parent.name, "mission_driven")
        self.assertEqual(second.memory_path.parent.name, "mission_driven")


if __name__ == "__main__":
    unittest.main()
