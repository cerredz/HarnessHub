from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from harnessiq.agents import AgentModelResponse, AgentRuntimeConfig, BaseAgent
from harnessiq.shared.agents import AgentModelRequest, AgentParameterSection
from harnessiq.tools.registry import ToolRegistry
from harnessiq.utils import JSONLLedgerSink, LedgerEntry
from harnessiq.utils.stats_projector import (
    StatsProjector,
    build_stats_summary,
    export_stats_csv,
    export_stats_json,
    load_stats_snapshots,
    stats_dir_for_ledger_path,
)


class _StaticModel:
    def __init__(self, responses: list[AgentModelResponse]) -> None:
        self._responses = list(responses)
        self._index = 0

    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        del request
        response = self._responses[self._index]
        self._index += 1
        return response


class _ProjectorAgent(BaseAgent):
    def __init__(self, *, model: _StaticModel, runtime_config: AgentRuntimeConfig, repo_root: Path) -> None:
        super().__init__(
            name="projector_agent",
            model=model,
            tool_executor=ToolRegistry([]),
            runtime_config=runtime_config,
            repo_root=repo_root,
        )

    def build_instance_payload(self) -> dict:
        return {"segment": "analytics"}

    def build_system_prompt(self) -> str:
        return "Projector prompt"

    def load_parameter_sections(self) -> list[AgentParameterSection]:
        return [AgentParameterSection(title="State", content="initial")]


class StatsProjectorTests(unittest.TestCase):
    def test_incremental_apply_matches_full_rebuild(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir, "runs.jsonl")
            entries = [
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
                    tool_breakdown={"read_file": 1, "write_memory": 2},
                ),
                _entry(
                    run_id="run-3",
                    status="error",
                    session_id="sess_B",
                    instance_id="instance-2",
                    started_at=_dt(30),
                    finished_at=_dt(32),
                    estimated_tokens=50,
                    reset_count=0,
                    cycles_completed=1,
                    tool_breakdown={"search_web": 1},
                    agent_name="email_agent",
                ),
            ]
            _write_ledger(ledger_path, entries)

            rebuild_projector = StatsProjector(ledger_path)
            rebuild_result = rebuild_projector.rebuild()
            self.assertEqual(rebuild_result.entries_processed, 3)
            rebuilt_snapshots = load_stats_snapshots(ledger_path)

            stats_dir = stats_dir_for_ledger_path(ledger_path)
            for path in stats_dir.glob("*.json"):
                path.unlink()

            incremental_projector = StatsProjector(ledger_path)
            for entry in entries:
                applied = incremental_projector.apply_entry(entry)
                self.assertTrue(applied)
            incremental_snapshots = load_stats_snapshots(ledger_path)

            self.assertEqual(incremental_snapshots, rebuilt_snapshots)
            session = rebuilt_snapshots["sessions"]["sess_A"]
            self.assertEqual(session["run_count"], 2)
            self.assertEqual(session["pause_count"], 1)
            self.assertEqual(session["total_cycles"], 5)
            self.assertEqual(session["session_tokens_estimated"], 300)
            agent = rebuilt_snapshots["agents"]["projector_agent"]
            self.assertEqual(agent["total_runs"], 2)
            self.assertEqual(agent["total_sessions"], 1)
            self.assertEqual(agent["top_tools"][0], {"tool_key": "read_file", "total_calls": 3})
            self.assertEqual(agent["top_tools"][1], {"tool_key": "write_memory", "total_calls": 2})

    def test_rebuild_skips_entries_without_valid_stats(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir, "runs.jsonl")
            valid_entry = _entry(
                run_id="run-1",
                status="completed",
                session_id="sess_A",
                instance_id="instance-1",
                started_at=_dt(0),
                finished_at=_dt(4),
                estimated_tokens=100,
                reset_count=0,
                cycles_completed=1,
                tool_breakdown={},
            )
            invalid_entry = LedgerEntry(
                run_id="run-invalid",
                agent_name="projector_agent",
                started_at=_dt(5),
                finished_at=_dt(6),
                status="completed",
                reset_count=0,
                outputs={},
                tags=[],
                metadata={},
            )
            _write_ledger(ledger_path, [valid_entry, invalid_entry])

            result = StatsProjector(ledger_path).rebuild()

            self.assertEqual(result.entries_processed, 2)
            self.assertEqual(result.entries_applied, 1)
            self.assertEqual(result.entries_skipped, 1)
            snapshots = load_stats_snapshots(ledger_path)
            self.assertEqual(snapshots["agents"]["projector_agent"]["total_runs"], 1)

    def test_export_helpers_emit_snapshot_json_and_flat_csv(self) -> None:
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
            StatsProjector(ledger_path).rebuild()

            exported_json = json.loads(export_stats_json(ledger_path))
            exported_csv = export_stats_csv(ledger_path)

            self.assertIn("agents", exported_json)
            self.assertIn("sessions", exported_json)
            self.assertIn("run_id,agent_name,repo_id", exported_csv)
            self.assertIn("run-1", exported_csv)

    def test_runtime_run_populates_stats_snapshots_after_ledger_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir, "repo")
            repo_root.mkdir()
            ledger_path = Path(temp_dir, "runs.jsonl")
            runtime_config = AgentRuntimeConfig(
                output_sinks=(JSONLLedgerSink(path=ledger_path),),
                include_default_output_sink=False,
            )
            agent = _ProjectorAgent(
                model=_StaticModel([AgentModelResponse(assistant_message="done", should_continue=False)]),
                runtime_config=runtime_config,
                repo_root=repo_root,
            )

            result = agent.run(max_cycles=1)

            self.assertEqual(result.status, "completed")
            stats_dir = stats_dir_for_ledger_path(ledger_path)
            self.assertTrue((stats_dir / "agents.json").exists())
            self.assertTrue((stats_dir / "sessions.json").exists())
            summary = build_stats_summary(ledger_path)
            self.assertEqual(summary["total_runs"], 1)
            self.assertEqual(summary["total_sessions"], 1)


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
