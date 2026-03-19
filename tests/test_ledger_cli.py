"""Tests for ledger/connect/report CLI commands."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from harnessiq.cli.main import build_parser, main


class LedgerCLITests(unittest.TestCase):
    def test_top_level_commands_are_registered(self) -> None:
        parser = build_parser()
        args, _ = parser.parse_known_args(["connect", "obsidian", "--vault-path", "vault"])
        self.assertEqual(args.connect_command, "obsidian")
        args, _ = parser.parse_known_args(["connections", "list"])
        self.assertEqual(args.connections_command, "list")
        args, _ = parser.parse_known_args(["export", "--format", "json"])
        self.assertEqual(args.command, "export")

    def test_connect_list_test_and_remove_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict("os.environ", {"HARNESSIQ_HOME": temp_dir}):
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = main(
                        [
                            "connect",
                            "obsidian",
                            "--vault-path",
                            str(Path(temp_dir, "vault")),
                            "--note-folder",
                            "Runs",
                        ]
                    )
                self.assertEqual(exit_code, 0)

                output = io.StringIO()
                with redirect_stdout(output):
                    main(["connections", "list"])
                listed = json.loads(output.getvalue())
                self.assertEqual(len(listed["connections"]), 1)
                self.assertEqual(listed["connections"][0]["sink_type"], "obsidian")

                output = io.StringIO()
                with redirect_stdout(output):
                    main(["connections", "test", "obsidian"])
                tested = json.loads(output.getvalue())
                self.assertEqual(tested["status"], "validated")

                output = io.StringIO()
                with redirect_stdout(output):
                    main(["connections", "remove", "obsidian"])
                removed = json.loads(output.getvalue())
                self.assertEqual(removed["status"], "removed")

    def test_export_and_report_read_from_local_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir, "runs.jsonl")
            ledger_path.write_text(
                json.dumps(
                    {
                        "agent_name": "linkedin_job_applier",
                        "finished_at": "2026-03-19T02:05:00Z",
                        "metadata": {"provider": "grok"},
                        "outputs": {"jobs_applied": [{"company": "Stripe"}]},
                        "reset_count": 1,
                        "run_id": "run-1",
                        "started_at": "2026-03-19T02:00:00Z",
                        "status": "completed",
                        "tags": ["linkedin", "jobs"],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            output = io.StringIO()
            with redirect_stdout(output):
                main(["export", "--format", "json", "--ledger-path", str(ledger_path)])
            exported = json.loads(output.getvalue())
            self.assertEqual(exported[0]["run_id"], "run-1")

            output = io.StringIO()
            with redirect_stdout(output):
                main(["report", "--format", "markdown", "--ledger-path", str(ledger_path)])
            self.assertIn("HarnessIQ Run Report", output.getvalue())

    def test_linkedin_run_accepts_per_run_sink_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            vault_path = Path(temp_dir, "vault")
            with patch.dict("os.environ", {"HARNESSIQ_HOME": str(Path(temp_dir, "home"))}):
                with redirect_stdout(io.StringIO()):
                    main(
                        [
                            "linkedin",
                            "configure",
                            "--agent",
                            "candidate-a",
                            "--memory-root",
                            temp_dir,
                            "--job-preferences-text",
                            "Platform roles.",
                            "--user-profile-text",
                            "Backend engineer.",
                        ]
                    )

                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = main(
                        [
                            "linkedin",
                            "run",
                            "--agent",
                            "candidate-a",
                            "--memory-root",
                            temp_dir,
                            "--model-factory",
                            "tests.test_linkedin_cli:create_static_model",
                            "--max-cycles",
                            "1",
                            "--sink",
                            f"obsidian:vault_path={vault_path.as_posix()},note_folder=Runs",
                        ]
                    )

                self.assertEqual(exit_code, 0)
                payload = json.loads(output.getvalue())
                self.assertEqual(payload["result"]["status"], "completed")
                note_files = list((vault_path / "Runs").glob("*.md"))
                self.assertEqual(len(note_files), 1)


if __name__ == "__main__":
    unittest.main()
