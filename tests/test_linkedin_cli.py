"""Tests for the LinkedIn CLI commands."""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from harnessiq.agents import AgentModelRequest, AgentModelResponse
from harnessiq.cli.main import main

_LAST_LANGSMITH_ENV: dict[str, str] = {}
_LAST_MODEL_PROFILE: dict[str, object] = {}
_LANGSMITH_CLIENT_PATCHER = patch("harnessiq.agents.base.agent.build_langsmith_client", return_value=None)


def setUpModule() -> None:
    _LANGSMITH_CLIENT_PATCHER.start()


def tearDownModule() -> None:
    _LANGSMITH_CLIENT_PATCHER.stop()


class _StaticModel:
    def __init__(self) -> None:
        self.requests: list[AgentModelRequest] = []

    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        self.requests.append(request)
        return AgentModelResponse(assistant_message="CLI run complete.", should_continue=False)


def create_static_model() -> _StaticModel:
    return _StaticModel()


def create_static_model_recording_langsmith_env() -> _StaticModel:
    global _LAST_LANGSMITH_ENV
    _LAST_LANGSMITH_ENV = {
        "LANGSMITH_API_KEY": os.environ.get("LANGSMITH_API_KEY", ""),
        "LANGCHAIN_API_KEY": os.environ.get("LANGCHAIN_API_KEY", ""),
        "LANGSMITH_PROJECT": os.environ.get("LANGSMITH_PROJECT", ""),
        "LANGCHAIN_PROJECT": os.environ.get("LANGCHAIN_PROJECT", ""),
    }
    return _StaticModel()


def create_static_model_from_profile(profile) -> _StaticModel:
    global _LAST_MODEL_PROFILE
    _LAST_MODEL_PROFILE = profile.as_dict()
    return _StaticModel()


def _extract_last_json_object(rendered: str) -> dict[str, object]:
    lines = rendered.splitlines()
    for index in range(len(lines) - 1, -1, -1):
        if lines[index].strip() != "{":
            continue
        candidate = "\n".join(lines[index:])
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    raise AssertionError(f"Expected a trailing JSON object in output:\n{rendered}")


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
            run_stderr = io.StringIO()
            with redirect_stdout(run_stdout), redirect_stderr(run_stderr):
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
            payload = _extract_last_json_object(run_stdout.getvalue())
            payload = json.loads(run_stdout.getvalue())
            self.assertTrue(payload["instance_id"].startswith("linkedin_job_applier::"))
            self.assertIsNotNone(payload["instance_name"])
            self.assertEqual(payload["result"]["status"], "completed")
            self.assertEqual(payload["result"]["cycles_completed"], 1)
            self.assertIn("DURABLE LINKEDIN APPLICATION RECORDS", run_stderr.getvalue())

    def test_run_seeds_langsmith_environment_from_repo_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            Path(temp_dir, ".env").write_text(
                "LANGCHAIN_API_KEY=ls_test_cli\nLANGCHAIN_PROJECT=cli-project\n",
                encoding="utf-8",
            )
            with redirect_stdout(io.StringIO()):
                main(
                    [
                        "linkedin",
                        "configure",
                        "--agent",
                        "candidate-c",
                        "--memory-root",
                        temp_dir,
                        "--job-preferences-text",
                        "Distributed systems roles.",
                        "--user-profile-text",
                        "Backend engineer profile.",
                    ]
                )

            with patch.dict(os.environ, {}, clear=True):
                run_stdout = io.StringIO()
                with (
                    patch(
                        "harnessiq.cli.common.load_factory",
                        return_value=create_static_model_recording_langsmith_env,
                    ),
                    redirect_stdout(run_stdout),
                ):
                    exit_code = main(
                        [
                            "linkedin",
                            "run",
                            "--agent",
                            "candidate-c",
                            "--memory-root",
                            temp_dir,
                            "--model-factory",
                            "mod:model",
                            "--max-cycles",
                            "1",
                        ]
                    )

            self.assertEqual(exit_code, 0)
            self.assertEqual(_LAST_LANGSMITH_ENV["LANGSMITH_API_KEY"], "ls_test_cli")
            self.assertEqual(_LAST_LANGSMITH_ENV["LANGCHAIN_API_KEY"], "ls_test_cli")
            self.assertEqual(_LAST_LANGSMITH_ENV["LANGSMITH_PROJECT"], "cli-project")
            self.assertEqual(_LAST_LANGSMITH_ENV["LANGCHAIN_PROJECT"], "cli-project")

    def test_run_accepts_persisted_model_profile(self) -> None:
        global _LAST_MODEL_PROFILE
        _LAST_MODEL_PROFILE = {}

        with tempfile.TemporaryDirectory() as temp_dir:
            home_dir = Path(temp_dir, "home")
            with patch.dict(os.environ, {"HARNESSIQ_HOME": str(home_dir)}):
                with redirect_stdout(io.StringIO()):
                    main(
                        [
                            "models",
                            "add",
                            "--name",
                            "work",
                            "--model",
                            "grok:grok-4-1-fast-reasoning",
                            "--reasoning-effort",
                            "high",
                        ]
                    )
                    main(
                        [
                            "linkedin",
                            "configure",
                            "--agent",
                            "candidate-d",
                            "--memory-root",
                            temp_dir,
                            "--job-preferences-text",
                            "Distributed systems roles.",
                            "--user-profile-text",
                            "Backend engineer profile.",
                        ]
                    )

                run_stdout = io.StringIO()
                with (
                    patch("harnessiq.cli.common.create_model_from_profile", side_effect=create_static_model_from_profile),
                    redirect_stdout(run_stdout),
                ):
                    exit_code = main(
                        [
                            "linkedin",
                            "run",
                            "--agent",
                            "candidate-d",
                            "--memory-root",
                            temp_dir,
                            "--profile",
                            "work",
                            "--max-cycles",
                            "1",
                        ]
                    )

            self.assertEqual(exit_code, 0)
            payload = json.loads(run_stdout.getvalue())
            self.assertEqual(payload["result"]["status"], "completed")
            self.assertEqual(_LAST_MODEL_PROFILE["name"], "work")
            self.assertEqual(_LAST_MODEL_PROFILE["provider"], "grok")
            self.assertEqual(_LAST_MODEL_PROFILE["model_name"], "grok-4-1-fast-reasoning")
            self.assertEqual(_LAST_MODEL_PROFILE["reasoning_effort"], "high")


if __name__ == "__main__":
    unittest.main()
