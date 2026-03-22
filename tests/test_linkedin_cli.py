"""Tests for the LinkedIn CLI commands."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from harnessiq.agents import AgentModelRequest, AgentModelResponse
from harnessiq.cli.main import main


class _StaticModel:
    def __init__(self) -> None:
        self.requests: list[AgentModelRequest] = []

    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        self.requests.append(request)
        return AgentModelResponse(assistant_message="CLI run complete.", should_continue=False)


def create_static_model() -> _StaticModel:
    return _StaticModel()


class LinkedInCLITests(unittest.TestCase):
    def test_configure_and_show_manage_linkedin_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_file = Path(temp_dir, "resume.txt")
            source_file.write_text("Resume content", encoding="utf-8")

            configure_stdout = io.StringIO()
            with redirect_stdout(configure_stdout):
                exit_code = main(
                    [
                        "linkedin",
                        "configure",
                        "--agent",
                        "candidate-a",
                        "--memory-root",
                        temp_dir,
                        "--job-preferences-text",
                        "Staff platform roles in New York.",
                        "--user-profile-text",
                        "Python, distributed systems, authorized to work in the US.",
                        "--runtime-param",
                        "max_tokens=2048",
                        "--runtime-param",
                        "notify_on_pause=false",
                        "--custom-param",
                        "team=platform",
                        "--custom-param",
                        "years_experience=8",
                        "--additional-prompt-text",
                        "Prioritize remote-friendly companies.",
                        "--import-file",
                        str(source_file),
                        "--inline-file",
                        "cover-letter.txt=Hello from the CLI.",
                    ]
                )

            self.assertEqual(exit_code, 0)
            configured_payload = json.loads(configure_stdout.getvalue())
            self.assertEqual(configured_payload["status"], "configured")
            self.assertEqual(configured_payload["runtime_parameters"]["max_tokens"], 2048)
            self.assertFalse(configured_payload["runtime_parameters"]["notify_on_pause"])
            self.assertEqual(configured_payload["custom_parameters"]["team"], "platform")
            self.assertEqual(len(configured_payload["managed_files"]), 2)

            show_stdout = io.StringIO()
            with redirect_stdout(show_stdout):
                exit_code = main(
                    [
                        "linkedin",
                        "show",
                        "--agent",
                        "candidate-a",
                        "--memory-root",
                        temp_dir,
                    ]
                )

            self.assertEqual(exit_code, 0)
            shown_payload = json.loads(show_stdout.getvalue())
            self.assertEqual(shown_payload["job_preferences"], "Staff platform roles in New York.")
            self.assertIn("cover-letter.txt", json.dumps(shown_payload["managed_files"]))
            self.assertIn("resume.txt", json.dumps(shown_payload["managed_files"]))
            self.assertTrue(Path(temp_dir, "candidate-a", "managed_files", "resume.txt").exists())

    def test_run_uses_persisted_state_and_factory_model(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with redirect_stdout(io.StringIO()):
                main(
                    [
                        "linkedin",
                        "configure",
                        "--agent",
                        "candidate-b",
                        "--memory-root",
                        temp_dir,
                        "--job-preferences-text",
                        "Distributed systems roles.",
                        "--user-profile-text",
                        "Backend engineer profile.",
                        "--runtime-param",
                        "max_tokens=1500",
                    ]
                )

            run_stdout = io.StringIO()
            with redirect_stdout(run_stdout):
                exit_code = main(
                    [
                        "linkedin",
                        "run",
                        "--agent",
                        "candidate-b",
                        "--memory-root",
                        temp_dir,
                        "--model-factory",
                        "tests.test_linkedin_cli:create_static_model",
                        "--max-cycles",
                        "1",
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(run_stdout.getvalue())
            self.assertTrue(payload["instance_id"].startswith("linkedin_job_applier::"))
            self.assertIsNotNone(payload["instance_name"])
            self.assertEqual(payload["result"]["status"], "completed")
            self.assertEqual(payload["result"]["cycles_completed"], 1)


if __name__ == "__main__":
    unittest.main()
