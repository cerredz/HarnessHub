"""Tests for the Instagram CLI commands."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from harnessiq.cli.main import build_parser, main
from harnessiq.shared.instagram import InstagramLeadRecord, InstagramMemoryStore

_LAST_LANGSMITH_ENV: dict[str, str] = {}
_LANGSMITH_CLIENT_PATCHER = patch("harnessiq.agents.base.agent.build_langsmith_client", return_value=None)


def setUpModule() -> None:
    _LANGSMITH_CLIENT_PATCHER.start()


def tearDownModule() -> None:
    _LANGSMITH_CLIENT_PATCHER.stop()


def _run(argv: list[str]) -> int:
    return main(argv)


def _recording_model_factory() -> MagicMock:
    global _LAST_LANGSMITH_ENV
    _LAST_LANGSMITH_ENV = {
        "LANGSMITH_API_KEY": os.environ.get("LANGSMITH_API_KEY", ""),
        "LANGCHAIN_API_KEY": os.environ.get("LANGCHAIN_API_KEY", ""),
        "LANGSMITH_PROJECT": os.environ.get("LANGSMITH_PROJECT", ""),
        "LANGCHAIN_PROJECT": os.environ.get("LANGCHAIN_PROJECT", ""),
    }
    model = MagicMock()
    model.generate_turn.return_value = MagicMock()
    return model


class InstagramCliTests(unittest.TestCase):
    def test_instagram_subcommand_registered(self) -> None:
        parser = build_parser()
        with self.assertRaises(SystemExit) as exc_info:
            parser.parse_args(["instagram", "--help"])
        self.assertEqual(exc_info.exception.code, 0)

    def test_get_emails_subcommand_registered(self) -> None:
        parser = build_parser()
        args, _ = parser.parse_known_args(["instagram", "get-emails", "--agent", "test"])
        self.assertEqual(args.instagram_command, "get-emails")

    def test_prepare_creates_memory_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("sys.stdout.write") as mock_write:
                result = _run(["instagram", "prepare", "--agent", "my-agent", "--memory-root", temp_dir])
            self.assertEqual(result, 0)
            self.assertTrue((Path(temp_dir) / "my-agent").is_dir())
            rendered = "".join(call.args[0] for call in mock_write.call_args_list)
            payload = json.loads(rendered)
            self.assertEqual(payload["status"], "prepared")

    def test_configure_sets_icps_and_runtime_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _run(["instagram", "prepare", "--agent", "a", "--memory-root", temp_dir])
            with patch("sys.stdout.write") as mock_write:
                result = _run(
                    [
                        "instagram",
                        "configure",
                        "--agent",
                        "a",
                        "--memory-root",
                        temp_dir,
                        "--icp",
                        "fitness creators",
                        "--icp",
                        "ugc skincare creators",
                        "--runtime-param",
                        "search_result_limit=3",
                        "--custom-param",
                        'target_segment="micro-creators"',
                    ]
                )
            self.assertEqual(result, 0)
            payload = json.loads("".join(call.args[0] for call in mock_write.call_args_list))
            self.assertEqual(payload["icp_profiles"], ["fitness creators", "ugc skincare creators"])
            self.assertEqual(payload["custom_parameters"]["target_segment"], "micro-creators")
            self.assertEqual(payload["runtime_parameters"]["search_result_limit"], 3)

    def test_show_returns_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _run(["instagram", "prepare", "--agent", "a", "--memory-root", temp_dir])
            with patch("sys.stdout.write") as mock_write:
                _run(["instagram", "show", "--agent", "a", "--memory-root", temp_dir])
            payload = json.loads("".join(call.args[0] for call in mock_write.call_args_list))
            self.assertEqual(payload["search_count"], 0)
            self.assertEqual(payload["email_count"], 0)

    def test_get_emails_reads_persisted_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = InstagramMemoryStore(memory_path=Path(temp_dir) / "a")
            store.prepare()
            store.merge_leads(
                [
                    InstagramLeadRecord(
                        source_url="https://www.instagram.com/creator-a/",
                        source_keyword="fitness coach",
                        found_at="2026-03-19T00:00:00Z",
                        emails=("creator@example.com",),
                    )
                ]
            )
            with patch("sys.stdout.write") as mock_write:
                result = _run(["instagram", "get-emails", "--agent", "a", "--memory-root", temp_dir])
            self.assertEqual(result, 0)
            payload = json.loads("".join(call.args[0] for call in mock_write.call_args_list))
            self.assertEqual(payload["emails"], ["creator@example.com"])
            self.assertEqual(payload["count"], 1)

    def test_run_invokes_agent_from_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _run(["instagram", "prepare", "--agent", "a", "--memory-root", temp_dir])
            _run(
                [
                    "instagram",
                    "configure",
                    "--agent",
                    "a",
                    "--memory-root",
                    temp_dir,
                    "--icp",
                    "fitness creators",
                ]
            )

            mock_agent = MagicMock()
            mock_result = MagicMock()
            mock_result.cycles_completed = 2
            mock_result.pause_reason = None
            mock_result.resets = 0
            mock_result.status = "completed"
            mock_agent.run.return_value = mock_result
            mock_agent.get_emails.return_value = ("creator@example.com",)

            with (
                patch(
                    "harnessiq.cli.instagram.commands._load_factory",
                    side_effect=[lambda: MagicMock(), lambda: object()],
                ),
                patch(
                    "harnessiq.agents.instagram.InstagramKeywordDiscoveryAgent.from_memory",
                    return_value=mock_agent,
                ) as patched_from_memory,
                patch("sys.stdout.write") as mock_write,
            ):
                result = _run(
                    [
                        "instagram",
                        "run",
                        "--agent",
                        "a",
                        "--memory-root",
                        temp_dir,
                        "--model-factory",
                        "mod:model",
                        "--custom-param",
                        'target_segment="micro-creators"',
                        "--icp",
                        "fitness creators",
                    ]
                )

            self.assertEqual(result, 0)
            payload = json.loads("".join(call.args[0] for call in mock_write.call_args_list))
            self.assertEqual(payload["email_count"], 1)
            self.assertEqual(payload["result"]["cycles_completed"], 2)
            self.assertEqual(
                patched_from_memory.call_args.kwargs["custom_overrides"],
                {
                    "icp_profiles": ["fitness creators"],
                    "target_segment": "micro-creators",
                },
            )

    def test_run_seeds_langsmith_environment_from_repo_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            Path(temp_dir, ".env").write_text(
                "LANGCHAIN_API_KEY=ls_test_instagram\nLANGCHAIN_PROJECT=instagram-project\n",
                encoding="utf-8",
            )
            _run(["instagram", "prepare", "--agent", "a", "--memory-root", temp_dir])
            _run(
                [
                    "instagram",
                    "configure",
                    "--agent",
                    "a",
                    "--memory-root",
                    temp_dir,
                    "--icp",
                    "fitness creators",
                ]
            )

            mock_agent = MagicMock()
            mock_result = MagicMock()
            mock_result.cycles_completed = 1
            mock_result.pause_reason = None
            mock_result.resets = 0
            mock_result.status = "completed"
            mock_agent.run.return_value = mock_result
            mock_agent.get_emails.return_value = ()

            with (
                patch.dict(os.environ, {}, clear=True),
                patch(
                    "harnessiq.cli.instagram.commands._load_factory",
                    side_effect=[_recording_model_factory, lambda: object()],
                ),
                patch(
                    "harnessiq.agents.instagram.InstagramKeywordDiscoveryAgent.from_memory",
                    return_value=mock_agent,
                ),
                patch("sys.stdout.write"),
            ):
                result = _run(
                    [
                        "instagram",
                        "run",
                        "--agent",
                        "a",
                        "--memory-root",
                        temp_dir,
                        "--model-factory",
                        "mod:model",
                    ]
                )

            self.assertEqual(result, 0)
            self.assertEqual(_LAST_LANGSMITH_ENV["LANGSMITH_API_KEY"], "ls_test_instagram")
            self.assertEqual(_LAST_LANGSMITH_ENV["LANGCHAIN_API_KEY"], "ls_test_instagram")
            self.assertEqual(_LAST_LANGSMITH_ENV["LANGSMITH_PROJECT"], "instagram-project")
            self.assertEqual(_LAST_LANGSMITH_ENV["LANGCHAIN_PROJECT"], "instagram-project")


if __name__ == "__main__":
    unittest.main()
