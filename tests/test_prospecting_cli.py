"""Tests for the Google Maps prospecting CLI commands."""

from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

from harnessiq.cli.main import build_parser, main
from harnessiq.shared.prospecting import ProspectingMemoryStore

_LAST_PROVIDER_ENV: dict[str, str] = {}


def _run(argv: list[str]) -> int:
    return main(argv)


def _recording_model_factory() -> MagicMock:
    global _LAST_PROVIDER_ENV
    _LAST_PROVIDER_ENV = {
        "XAI_API_KEY": os.environ.get("XAI_API_KEY", ""),
    }
    model = MagicMock()
    model.generate_turn.return_value = MagicMock()
    return model


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
                    "harnessiq.cli.common.load_factory",
                    return_value=lambda: MagicMock(),
                ),
                patch(
                    "harnessiq.cli.prospecting.commands._load_factory",
                    return_value=lambda: (),
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

    def test_run_requires_configured_company_description(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            _run(["prospecting", "prepare", "--agent", "nj-dentists", "--memory-root", temp_dir])

            with self.assertRaisesRegex(ValueError, "prospecting configure --company-description-text"):
                _run(
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

    def test_run_seeds_provider_environment_from_local_env_before_model_factory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            Path(temp_dir, "local.env").write_text("XAI_API_KEY=local-xai-key\n", encoding="utf-8")
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
            mock_result.cycles_completed = 1
            mock_result.pause_reason = None
            mock_result.resets = 0
            mock_result.status = "completed"
            mock_agent.run.return_value = mock_result

            with (
                patch.dict(os.environ, {}, clear=True),
                patch(
                    "harnessiq.cli.common.load_factory",
                    return_value=_recording_model_factory,
                ),
                patch(
                    "harnessiq.cli.prospecting.commands._load_factory",
                    return_value=lambda: (),
                ),
                patch(
                    "harnessiq.agents.GoogleMapsProspectingAgent.from_memory",
                    return_value=mock_agent,
                ),
                patch("sys.stdout.write"),
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
            self.assertEqual(_LAST_PROVIDER_ENV["XAI_API_KEY"], "local-xai-key")

    def test_init_browser_uses_persistent_session_dir_and_emits_saved_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            session = MagicMock()
            stdout = io.StringIO()

            with (
                patch(
                    "harnessiq.integrations.google_maps_playwright.PlaywrightGoogleMapsSession",
                    return_value=session,
                ) as mock_session_class,
                patch("harnessiq.cli.prospecting.commands.emit_json") as mock_emit_json,
                patch("builtins.input", return_value=""),
                redirect_stdout(stdout),
            ):
                result = _run(
                    [
                        "prospecting",
                        "init-browser",
                        "--agent",
                        "nj-dentists",
                        "--memory-root",
                        temp_dir,
                    ]
                )

        self.assertEqual(result, 0)
        browser_data_dir = str(Path(temp_dir, "nj-dentists", "browser-data").resolve())
        mock_session_class.assert_called_once_with(
            session_dir=Path(temp_dir, "nj-dentists", "browser-data"),
            channel="chrome",
            headless=False,
        )
        session.start.assert_called_once_with()
        session.stop.assert_called_once_with()
        payload = mock_emit_json.call_args.args[0]
        self.assertEqual(payload["browser_data_dir"], browser_data_dir)
        self.assertEqual(payload["status"], "session_saved")


if __name__ == "__main__":
    unittest.main()
