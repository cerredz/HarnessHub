"""Tests for the Google Maps prospecting CLI commands."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from harnessiq.cli.main import build_parser, main
from harnessiq.shared.prospecting import ProspectingMemoryStore


def _run(argv: list[str]) -> int:
    return main(argv)


class ProspectingCliTests(unittest.TestCase):
    def test_prospecting_subcommand_registered(self) -> None:
        parser = build_parser()
        with self.assertRaises(SystemExit) as exc_info:
            parser.parse_args(["prospecting", "--help"])
        self.assertEqual(exc_info.exception.code, 0)

    def test_prepare_and_configure_manage_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("sys.stdout.write") as mock_write:
                result = _run(["prospecting", "prepare", "--agent", "nj-dentists", "--memory-root", temp_dir])
            self.assertEqual(result, 0)
            prepared = json.loads("".join(call.args[0] for call in mock_write.call_args_list))
            self.assertEqual(prepared["status"], "prepared")

            eval_prompt_path = Path(temp_dir) / "eval_prompt.txt"
            eval_prompt_path.write_text("Return strict JSON.", encoding="utf-8")

            with patch("sys.stdout.write") as mock_write:
                result = _run(
                    [
                        "prospecting",
                        "configure",
                        "--agent",
                        "nj-dentists",
                        "--memory-root",
                        temp_dir,
                        "--company-description-text",
                        "Owner-operated dental practices in New Jersey.",
                        "--agent-identity-text",
                        "Prospecting closer.",
                        "--additional-prompt-text",
                        "Prioritize outdated sites.",
                        "--runtime-param",
                        "max_tokens=4096",
                        "--custom-param",
                        "max_searches_per_run=12",
                        "--custom-param",
                        "website_inspect_enabled=false",
                        "--eval-system-prompt-file",
                        str(eval_prompt_path),
                    ]
                )
            self.assertEqual(result, 0)
            payload = json.loads("".join(call.args[0] for call in mock_write.call_args_list))
            self.assertEqual(payload["status"], "configured")
            self.assertEqual(payload["runtime_parameters"]["max_tokens"], 4096)
            self.assertEqual(payload["custom_parameters"]["max_searches_per_run"], 12)
            self.assertFalse(payload["custom_parameters"]["website_inspect_enabled"])
            self.assertEqual(payload["custom_parameters"]["eval_system_prompt"], "Return strict JSON.")

    def test_show_returns_run_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ProspectingMemoryStore(memory_path=Path(temp_dir) / "hvac")
            store.prepare()
            store.write_company_description("Owner-operated HVAC companies in central New Jersey")

            with patch("sys.stdout.write") as mock_write:
                result = _run(["prospecting", "show", "--agent", "hvac", "--memory-root", temp_dir])
            self.assertEqual(result, 0)
            payload = json.loads("".join(call.args[0] for call in mock_write.call_args_list))
            self.assertIn("HVAC companies", payload["company_description"])
            self.assertEqual(payload["qualified_lead_count"], 0)
            self.assertEqual(payload["run_state"]["last_completed_search_index"], -1)

    def test_run_invokes_agent_from_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _run(["prospecting", "prepare", "--agent", "nj-dentists", "--memory-root", temp_dir])
            _run(
                [
                    "prospecting",
                    "configure",
                    "--agent",
                    "nj-dentists",
                    "--memory-root",
                    temp_dir,
                    "--company-description-text",
                    "Owner-operated dental practices in New Jersey.",
                ]
            )

            mock_agent = MagicMock()
            mock_agent.last_run_id = "run-123"
            mock_result = MagicMock()
            mock_result.cycles_completed = 3
            mock_result.pause_reason = None
            mock_result.resets = 1
            mock_result.status = "completed"
            mock_agent.run.return_value = mock_result

            with (
                patch(
                    "harnessiq.cli.prospecting.commands._load_factory",
                    side_effect=[lambda: MagicMock(), lambda: ()],
                ),
                patch(
                    "harnessiq.agents.GoogleMapsProspectingAgent.from_memory",
                    return_value=mock_agent,
                ),
                patch("sys.stdout.write") as mock_write,
            ):
                result = _run(
                    [
                        "prospecting",
                        "run",
                        "--agent",
                        "nj-dentists",
                        "--memory-root",
                        temp_dir,
                        "--model-factory",
                        "mod:model",
                    ]
                )

            self.assertEqual(result, 0)
            payload = json.loads("".join(call.args[0] for call in mock_write.call_args_list))
            self.assertEqual(payload["ledger_run_id"], "run-123")
            self.assertEqual(payload["result"]["cycles_completed"], 3)
            self.assertEqual(payload["result"]["resets"], 1)


if __name__ == "__main__":
    unittest.main()
