"""Tests for the LinkedIn job application agent harness."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from harnessiq.agents import (
    AgentModelRequest,
    AgentModelResponse,
    LinkedInJobApplierAgent,
    build_linkedin_browser_tool_definitions,
)
from harnessiq.shared.agents import AgentRuntimeConfig
from harnessiq.shared.linkedin import DEFAULT_LINKEDIN_ACTION_LOG_WINDOW, LinkedInAgentConfig
from harnessiq.shared.tools import ToolCall

_LANGSMITH_CLIENT_PATCHER = patch("harnessiq.agents.base.agent.build_langsmith_client", return_value=None)


def setUpModule() -> None:
    _LANGSMITH_CLIENT_PATCHER.start()


def tearDownModule() -> None:
    _LANGSMITH_CLIENT_PATCHER.stop()


class _FakeModel:
    def __init__(self, responses: list[AgentModelResponse]) -> None:
        self._responses = list(responses)
        self.requests: list[AgentModelRequest] = []

    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        self.requests.append(request)
        return self._responses[len(self.requests) - 1]


class LinkedInJobApplierAgentTests(unittest.TestCase):
    def test_shared_linkedin_config_normalizes_paths_and_validates_window(self) -> None:
        config = LinkedInAgentConfig(memory_path="memory")

        self.assertEqual(config.memory_path, Path("memory"))
        with self.assertRaises(ValueError):
            LinkedInAgentConfig(memory_path="memory", action_log_window=0)

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
            self.assertTrue(Path(temp_dir, "runtime_parameters.json").exists())
            self.assertTrue(Path(temp_dir, "custom_parameters.json").exists())
            self.assertTrue(Path(temp_dir, "additional_prompt.md").exists())
            self.assertTrue(Path(temp_dir, "applied_jobs.jsonl").exists())
            self.assertTrue(Path(temp_dir, "action_log.jsonl").exists())
            self.assertTrue(Path(temp_dir, "managed_files.json").exists())
            self.assertTrue(Path(temp_dir, "screenshots").exists())
            self.assertTrue(Path(temp_dir, "managed_files").exists())
            self.assertIn("[IDENTITY]", model.requests[0].system_prompt)
            self.assertIn("[GOAL]", model.requests[0].system_prompt)
            self.assertIn("navigate", model.requests[0].system_prompt)
            self.assertIn("pause_and_notify", model.requests[0].system_prompt)
            self.assertEqual(agent.config.action_log_window, DEFAULT_LINKEDIN_ACTION_LOG_WINDOW)
            self.assertEqual(
                [section.title for section in model.requests[0].parameter_sections],
                [
                    "Job Preferences",
                    "User Profile",
                    "Jobs Already Applied To",
                    "Recent Actions (last 10)",
                ],
            )

    def test_memory_store_supports_runtime_params_custom_inputs_and_managed_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_file = Path(temp_dir, "resume.txt")
            source_file.write_text("Resume content", encoding="utf-8")
            model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])

            store = LinkedInJobApplierAgent(model=model, memory_path=temp_dir).memory_store
            store.prepare()
            store.write_runtime_parameters({"max_tokens": 1234, "notify_on_pause": False})
            store.write_custom_parameters({"target_level": "staff", "remote_only": True})
            store.write_additional_prompt("Prefer companies with strong infrastructure teams.")
            copied_file = store.ingest_managed_file(source_file)
            inline_file = store.write_managed_text_file(name="cover-letter.txt", content="Intro paragraph")

            agent = LinkedInJobApplierAgent.from_memory(model=model, memory_path=temp_dir)
            sections = {section.title: section.content for section in agent.load_parameter_sections()}

            self.assertEqual(agent.config.max_tokens, 1234)
            self.assertFalse(agent.config.notify_on_pause)
            self.assertIn("Runtime Parameters", sections)
            self.assertIn("Custom Parameters", sections)
            self.assertIn("Additional Prompt Data", sections)
            self.assertIn("Managed Files", sections)
            self.assertIn("resume.txt", sections["Managed Files"])
            self.assertIn("cover-letter.txt", sections["Managed Files"])
            self.assertTrue(Path(temp_dir, copied_file.relative_path).exists())
            self.assertTrue(Path(temp_dir, inline_file.relative_path).exists())

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
            # max_tokens is sized to accommodate the master_prompt.md base (~5519 tokens)
            # while still triggering a reset once the first transcript turn is appended.
            agent = LinkedInJobApplierAgent(
                model=model,
                memory_path=temp_dir,
                max_tokens=5900,
                reset_threshold=0.95,
            )

            result = agent.run(max_cycles=3)

            self.assertEqual(result.status, "completed")
            self.assertEqual(result.resets, 1)
            self.assertEqual(model.requests[1].transcript, ())
            self.assertIn("Navigated to LinkedIn Jobs", model.requests[1].parameter_sections[-1].content)

    def test_runtime_config_preserves_langsmith_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = LinkedInJobApplierAgent(
                model=_FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)]),
                memory_path=temp_dir,
                runtime_config=AgentRuntimeConfig(
                    langsmith_api_key="ls_test_sdk",
                    langsmith_project="linkedin-project",
                ),
            )

            self.assertEqual(agent.runtime_config.langsmith_api_key, "ls_test_sdk")
            self.assertEqual(agent.runtime_config.langsmith_project, "linkedin-project")


if __name__ == "__main__":
    unittest.main()
