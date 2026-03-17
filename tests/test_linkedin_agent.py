"""Tests for the LinkedIn job application agent harness."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harnessiq.agents import (
    AgentModelRequest,
    AgentModelResponse,
    JobSearchConfig,
    LinkedInJobApplierAgent,
    build_linkedin_browser_tool_definitions,
)
from harnessiq.shared.linkedin import DEFAULT_LINKEDIN_ACTION_LOG_WINDOW, LinkedInAgentConfig
from harnessiq.shared.tools import ToolCall


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
            self.assertTrue(Path(temp_dir, "job_search_config.json").exists())
            self.assertEqual(
                [section.title for section in model.requests[0].parameter_sections],
                [
                    "Jobs Already Applied To",
                    "Job Preferences",
                    "User Profile",
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
            self.assertIn("Additional Prompt Data", sections)  # section title updated in ticket 3
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

    def test_job_search_config_injected_into_context_window(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])

            # String description is persisted during prepare() and rendered into context.
            agent = LinkedInJobApplierAgent(
                model=model,
                memory_path=temp_dir,
                job_search_config="Senior software engineer, remote, salary > $150k",
            )
            result = agent.run(max_cycles=1)

            self.assertEqual(result.status, "completed")
            sections = {s.title: s.content for s in model.requests[0].parameter_sections}
            self.assertIn("Job Search Config", sections)
            self.assertIn("Senior software engineer", sections["Job Search Config"])
            # Applied jobs is still first even when job_search_config is present.
            self.assertEqual(model.requests[0].parameter_sections[0].title, "Jobs Already Applied To")
            self.assertEqual(model.requests[0].parameter_sections[1].title, "Job Search Config")

    def test_job_search_config_structured_fields_render_correctly(self) -> None:
        config = JobSearchConfig(
            title="Staff Engineer",
            location="San Francisco, CA",
            remote_type="remote",
            experience_levels=("mid_senior", "director"),
            date_posted="past_week",
            easy_apply_only=True,
            salary_min=200_000,
            salary_max=350_000,
            job_type=("full_time", "contract"),
        )
        rendered = config.render()
        self.assertIn("Staff Engineer", rendered)
        self.assertIn("San Francisco, CA", rendered)
        self.assertIn("Remote", rendered)
        self.assertIn("Mid Senior", rendered)
        self.assertIn("Past Week", rendered)
        self.assertIn("Easy Apply Only: Yes", rendered)
        self.assertIn("$200,000", rendered)
        self.assertIn("$350,000", rendered)
        self.assertIn("Full Time", rendered)

        roundtripped = JobSearchConfig.from_dict(config.as_dict())
        self.assertEqual(roundtripped.title, config.title)
        self.assertEqual(roundtripped.remote_type, config.remote_type)
        self.assertEqual(roundtripped.experience_levels, config.experience_levels)
        self.assertEqual(roundtripped.easy_apply_only, config.easy_apply_only)
        self.assertEqual(roundtripped.salary_min, config.salary_min)

    def test_job_search_config_from_memory_override_takes_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])
            store = LinkedInJobApplierAgent(model=model, memory_path=temp_dir).memory_store
            store.prepare()
            # Persist one config via the store.
            store.write_job_search_config({"title": "Product Manager"})

            # Override via from_memory() with a different config.
            override_config = JobSearchConfig(title="Engineering Manager", location="NYC")
            agent = LinkedInJobApplierAgent.from_memory(
                model=model,
                memory_path=temp_dir,
                job_search_config=override_config,
            )
            agent.run(max_cycles=1)
            sections = {s.title: s.content for s in model.requests[0].parameter_sections}
            self.assertIn("Engineering Manager", sections["Job Search Config"])

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


if __name__ == "__main__":
    unittest.main()
