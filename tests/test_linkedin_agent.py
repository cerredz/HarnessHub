"""Tests for the LinkedIn job application agent harness."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.agents import (
    AgentModelRequest,
    AgentModelResponse,
    LinkedInJobApplierAgent,
    build_linkedin_browser_tool_definitions,
)
from src.shared.tools import ToolCall


class _FakeModel:
    def __init__(self, responses: list[AgentModelResponse]) -> None:
        self._responses = list(responses)
        self.requests: list[AgentModelRequest] = []

    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        self.requests.append(request)
        return self._responses[len(self.requests) - 1]


class LinkedInJobApplierAgentTests(unittest.TestCase):
    def test_public_browser_tool_definitions_cover_the_linkedin_browser_surface(self) -> None:
        definitions = build_linkedin_browser_tool_definitions()

        self.assertEqual(definitions[0].name, "navigate")
        self.assertEqual(definitions[-1].name, "get_current_url")
        self.assertEqual(len(definitions), 14)

    def test_run_bootstraps_memory_files_and_injects_linkedin_prompt_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])
            agent = LinkedInJobApplierAgent(model=model, memory_path=temp_dir)

            result = agent.run(max_cycles=1)

            self.assertEqual(result.status, "completed")
            self.assertTrue(Path(temp_dir, "job_preferences.md").exists())
            self.assertTrue(Path(temp_dir, "user_profile.md").exists())
            self.assertTrue(Path(temp_dir, "agent_identity.md").exists())
            self.assertTrue(Path(temp_dir, "applied_jobs.jsonl").exists())
            self.assertTrue(Path(temp_dir, "action_log.jsonl").exists())
            self.assertTrue(Path(temp_dir, "screenshots").exists())
            self.assertIn("[IDENTITY]", model.requests[0].system_prompt)
            self.assertIn("[GOAL]", model.requests[0].system_prompt)
            self.assertIn("navigate", model.requests[0].system_prompt)
            self.assertIn("pause_and_notify", model.requests[0].system_prompt)
            self.assertEqual(
                [section.title for section in model.requests[0].parameter_sections],
                [
                    "Job Preferences",
                    "User Profile",
                    "Jobs Already Applied To",
                    "Recent Actions (last 10)",
                ],
            )

    def test_memory_tools_append_update_and_read_append_only_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])

            def save_screenshot(output_path: Path, label: str) -> None:
                output_path.write_bytes(b"fake-image")

            agent = LinkedInJobApplierAgent(
                model=model,
                memory_path=temp_dir,
                screenshot_persistor=save_screenshot,
            )
            agent.prepare()

            append_result = agent.tool_executor.execute(
                "linkedin.append_company",
                {
                    "job_id": "job-1",
                    "title": "Senior Product Manager",
                    "company": "Acme",
                    "url": "https://www.linkedin.com/jobs/view/job-1",
                    "easy_apply": True,
                },
            )
            update_result = agent.tool_executor.execute(
                "linkedin.update_job_status",
                {
                    "job_id": "job-1",
                    "status": "failed",
                    "notes": "Form requested unsupported question",
                },
            )
            skipped_result = agent.tool_executor.execute(
                "linkedin.mark_job_skipped",
                {
                    "job_id": "job-2",
                    "title": "Staff Engineer",
                    "company": "Beta",
                    "url": "https://www.linkedin.com/jobs/view/job-2",
                    "reason": "seniority mismatch",
                },
            )
            read_result = agent.tool_executor.execute(
                "linkedin.read_memory_file",
                {"filename": "applied_jobs.jsonl"},
            )
            screenshot_result = agent.tool_executor.execute(
                "linkedin.save_screenshot_to_memory",
                {"label": "recent state"},
            )

            self.assertEqual(append_result.output["status"], "applied")
            self.assertEqual(update_result.output["status"], "failed")
            self.assertEqual(skipped_result.output["status"], "skipped")
            self.assertIn("job-1", read_result.output["content"])
            self.assertTrue(Path(screenshot_result.output["path"]).exists())
            self.assertEqual(len(agent.memory_store.read_applied_jobs()), 3)
            self.assertEqual(agent.memory_store.current_jobs()["job-1"].status, "failed")
            self.assertEqual(agent.memory_store.current_jobs()["job-2"].status, "skipped")

    def test_context_reset_reloads_recent_actions_from_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model = _FakeModel(
                [
                    AgentModelResponse(
                        assistant_message="x" * 400,
                        tool_calls=(
                            ToolCall(
                                tool_key="linkedin.append_action",
                                arguments={
                                    "action": "Navigated to LinkedIn Jobs",
                                    "result": "Found 2 matching listings",
                                },
                            ),
                        ),
                        should_continue=True,
                    ),
                    AgentModelResponse(
                        assistant_message="done",
                        should_continue=False,
                    ),
                ]
            )
            agent = LinkedInJobApplierAgent(
                model=model,
                memory_path=temp_dir,
                max_tokens=3000,
                reset_threshold=0.95,
            )

            result = agent.run(max_cycles=3)

            self.assertEqual(result.status, "completed")
            self.assertEqual(result.resets, 1)
            self.assertEqual(model.requests[1].transcript, ())
            self.assertIn("Navigated to LinkedIn Jobs", model.requests[1].parameter_sections[-1].content)


if __name__ == "__main__":
    unittest.main()
