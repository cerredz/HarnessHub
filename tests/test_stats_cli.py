"""Tests for the ``harnessiq stats`` CLI family."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

from harnessiq.cli.main import build_parser, main
from harnessiq.utils import LedgerEntry


class StatsCLITests(unittest.TestCase):
    def test_top_level_stats_commands_are_registered(self) -> None:
        parser = build_parser()
        args, _ = parser.parse_known_args(["stats", "summary"])
        self.assertEqual(args.command, "stats")
        self.assertEqual(args.stats_command, "summary")
        args, _ = parser.parse_known_args(["stats", "agent", "projector_agent"])
        self.assertEqual(args.stats_command, "agent")
        args, _ = parser.parse_known_args(["stats", "export", "--format", "json"])
        self.assertEqual(args.stats_command, "export")

    def test_rebuild_summary_and_lookup_commands_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir, "runs.jsonl")
            _write_ledger(
                ledger_path,
                [
                    _entry(
                        run_id="run-1",
                        status="paused",
                        session_id="sess_A",
                        instance_id="instance-1",
                        started_at=_dt(0),
                        finished_at=_dt(5),
                        estimated_tokens=100,
                        reset_count=1,
                        cycles_completed=2,
                        tool_breakdown={"read_file": 2},
                    ),
                    _entry(
                        run_id="run-2",
                        status="completed",
                        session_id="sess_A",
                        instance_id="instance-1",
                        started_at=_dt(10),
                        finished_at=_dt(25),
                        estimated_tokens=200,
                        reset_count=0,
                        cycles_completed=3,
                        tool_breakdown={"write_memory": 2},
                    ),
                ],
            )

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["stats", "rebuild", "--ledger-path", str(ledger_path)])
            self.assertEqual(exit_code, 0)
            self.assertIn("Entries processed", output.getvalue())

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["stats", "summary", "--ledger-path", str(ledger_path)])
            self.assertEqual(exit_code, 0)
            summary_text = output.getvalue()
            self.assertIn("HarnessIQ Stats Summary", summary_text)
            self.assertIn("Total runs", summary_text)
            self.assertIn("projector_agent", summary_text)

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["stats", "agent", "projector_agent", "--format", "json", "--ledger-path", str(ledger_path)])
            self.assertEqual(exit_code, 0)
            agent_payload = json.loads(output.getvalue())
            self.assertEqual(agent_payload["total_runs"], 2)
            self.assertEqual(agent_payload["total_sessions"], 1)

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["stats", "session", "sess_A", "--format", "json", "--ledger-path", str(ledger_path)])
            self.assertEqual(exit_code, 0)
            session_payload = json.loads(output.getvalue())
            self.assertEqual(session_payload["run_ids"], ["run-1", "run-2"])
            self.assertEqual(session_payload["pause_count"], 1)

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["stats", "instance", "instance-1", "--format", "json", "--ledger-path", str(ledger_path)])
            self.assertEqual(exit_code, 0)
            instance_payload = json.loads(output.getvalue())
            self.assertEqual(instance_payload["total_runs"], 2)
            self.assertEqual(instance_payload["agent_name"], "projector_agent")

    def test_export_command_supports_stdout_and_file_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir, "runs.jsonl")
            _write_ledger(
                ledger_path,
                [
                    _entry(
                        run_id="run-1",
                        status="completed",
                        session_id="sess_A",
                        instance_id="instance-1",
                        started_at=_dt(0),
                        finished_at=_dt(4),
                        estimated_tokens=100,
                        reset_count=0,
                        cycles_completed=1,
                        tool_breakdown={"read_file": 2},
                    )
                ],
            )
            main(["stats", "rebuild", "--ledger-path", str(ledger_path)])

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["stats", "export", "--format", "csv", "--ledger-path", str(ledger_path)])
            self.assertEqual(exit_code, 0)
            self.assertIn("run_id,agent_name,repo_id", output.getvalue())

            export_path = Path(temp_dir, "exports", "stats.json")
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(
                    [
                        "stats",
                        "export",
                        "--format",
                        "json",
                        "--ledger-path",
                        str(ledger_path),
                        "--output",
                        str(export_path),
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertTrue(export_path.exists())
            exported = json.loads(export_path.read_text(encoding="utf-8"))
            self.assertIn("agents", exported)
            self.assertIn("Wrote json stats export", output.getvalue())


def _entry(
    *,
    run_id: str,
    status: str,
    session_id: str,
    instance_id: str,
    started_at: datetime,
    finished_at: datetime,
    estimated_tokens: int,
    reset_count: int,
    cycles_completed: int,
    tool_breakdown: dict[str, int],
    agent_name: str = "projector_agent",
) -> LedgerEntry:
    duration_seconds = max(0.0, (finished_at - started_at).total_seconds())
    return LedgerEntry(
        run_id=run_id,
        agent_name=agent_name,
        started_at=started_at,
        finished_at=finished_at,
        status=status,  # type: ignore[arg-type]
        reset_count=reset_count,
        outputs={},
        tags=[],
        metadata={
            "stats": {
                "version": 1,
                "repo_id": "repo",
                "instance_id": instance_id,
                "session_id": session_id,
                "model_provider": "custom",
                "model_name": "StaticModel",
                "token_usage": {
                    "request_estimated": estimated_tokens,
                    "input_actual": None,
                    "output_actual": None,
                    "total_actual": None,
                    "source": "estimated",
                },
                "timing": {
                    "run_started_at": started_at.isoformat().replace("+00:00", "Z"),
                    "run_finished_at": finished_at.isoformat().replace("+00:00", "Z"),
                    "duration_seconds": duration_seconds,
                },
                "counters": {
                    "cycles_completed": cycles_completed,
                    "reset_count": reset_count,
                    "tool_calls": sum(tool_breakdown.values()),
                    "distinct_tools": len(tool_breakdown),
                    "tool_call_breakdown": tool_breakdown,
                },
                "run_status": status,
            }
        },
    )


def _write_ledger(path: Path, entries: list[LedgerEntry]) -> None:
    path.write_text(
        "\n".join(json.dumps(entry.as_dict(), sort_keys=True) for entry in entries) + "\n",
        encoding="utf-8",
    )


def _dt(offset_seconds: int) -> datetime:
    return datetime(2026, 3, 20, tzinfo=timezone.utc) + timedelta(seconds=offset_seconds)
