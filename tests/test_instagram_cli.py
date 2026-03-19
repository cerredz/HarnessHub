"""Tests for the Instagram CLI commands."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from harnessiq.cli.main import build_parser, main
from harnessiq.shared.instagram import InstagramLeadRecord, InstagramMemoryStore


def _run(argv: list[str]) -> int:
    return main(argv)


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
                    ]
                )
            self.assertEqual(result, 0)
            payload = json.loads("".join(call.args[0] for call in mock_write.call_args_list))
            self.assertEqual(payload["icp_profiles"], ["fitness creators", "ugc skincare creators"])
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
                ),
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
                    ]
                )

            self.assertEqual(result, 0)
            payload = json.loads("".join(call.args[0] for call in mock_write.call_args_list))
            self.assertEqual(payload["email_count"], 1)
            self.assertEqual(payload["result"]["cycles_completed"], 2)


if __name__ == "__main__":
    unittest.main()
