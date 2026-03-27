"""Tests for the ExaOutreach CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from harnessiq.cli.exa_outreach.commands import (
    SUPPORTED_EXA_OUTREACH_RUNTIME_PARAMETERS,
    normalize_exa_outreach_runtime_parameters,
    register_exa_outreach_commands,
)
from harnessiq.cli.main import build_parser, main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(argv: list[str]) -> int:
    return main(argv)


def _parse(argv: list[str]):
    parser = build_parser()
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Parser registration
# ---------------------------------------------------------------------------


class TestParserRegistration:
    def test_outreach_subcommand_registered(self):
        parser = build_parser()
        # --help triggers SystemExit(0) — that confirms the subcommand is registered
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["outreach", "--help"])
        assert exc_info.value.code == 0

    def test_prepare_subcommand_registered(self):
        # argparse exits with SystemExit on --help; use parse_known_args to avoid
        parser = build_parser()
        args, _ = parser.parse_known_args(["outreach", "prepare", "--agent", "test"])
        assert args.outreach_command == "prepare"

    def test_configure_subcommand_registered(self):
        parser = build_parser()
        args, _ = parser.parse_known_args(["outreach", "configure", "--agent", "test"])
        assert args.outreach_command == "configure"

    def test_show_subcommand_registered(self):
        parser = build_parser()
        args, _ = parser.parse_known_args(["outreach", "show", "--agent", "test"])
        assert args.outreach_command == "show"

    def test_run_subcommand_registered(self):
        parser = build_parser()
        args, _ = parser.parse_known_args([
            "outreach", "run",
            "--agent", "test",
            "--model-factory", "mod:fn",
            "--exa-credentials-factory", "mod:fn",
            "--resend-credentials-factory", "mod:fn",
            "--email-data-factory", "mod:fn",
        ])
        assert args.outreach_command == "run"


# ---------------------------------------------------------------------------
# prepare command
# ---------------------------------------------------------------------------


class TestPrepareCommand:
    def test_prepare_creates_memory_folder(self, tmp_path):
        result = _run([
            "outreach", "prepare",
            "--agent", "my-agent",
            "--memory-root", str(tmp_path),
        ])
        assert result == 0
        assert (tmp_path / "my-agent").is_dir()

    def test_prepare_emits_json_with_status(self, tmp_path, capsys):
        _run([
            "outreach", "prepare",
            "--agent", "my-agent",
            "--memory-root", str(tmp_path),
        ])
        out = capsys.readouterr().out
        payload = json.loads(out)
        assert payload["status"] == "prepared"
        assert payload["agent"] == "my-agent"
        assert "memory_path" in payload

    def test_prepare_default_memory_root(self, tmp_path, capsys):
        # Run with default memory-root; should not raise
        with patch("harnessiq.cli.builders.exa_outreach.ExaOutreachMemoryStore") as MockStore:
            instance = MagicMock()
            instance.memory_path.resolve.return_value = tmp_path / "my-agent"
            MockStore.return_value = instance
            result = _run(["outreach", "prepare", "--agent", "my-agent"])
        assert result == 0

    def test_prepare_slugifies_agent_name(self, tmp_path):
        _run([
            "outreach", "prepare",
            "--agent", "My Agent Name!",
            "--memory-root", str(tmp_path),
        ])
        assert (tmp_path / "My-Agent-Name").is_dir()


# ---------------------------------------------------------------------------
# configure command
# ---------------------------------------------------------------------------


class TestConfigureCommand:
    def test_configure_sets_search_query_text(self, tmp_path, capsys):
        # prepare first
        _run(["outreach", "prepare", "--agent", "a", "--memory-root", str(tmp_path)])
        capsys.readouterr()  # clear

        result = _run([
            "outreach", "configure",
            "--agent", "a",
            "--memory-root", str(tmp_path),
            "--query-text", "VP of Engineering",
        ])
        assert result == 0
        out = json.loads(capsys.readouterr().out)
        assert "search_query" in out["updated"]
        assert out["query_config"]["search_query"] == "VP of Engineering"

    def test_configure_sets_agent_identity_text(self, tmp_path, capsys):
        _run(["outreach", "prepare", "--agent", "a", "--memory-root", str(tmp_path)])
        capsys.readouterr()

        result = _run([
            "outreach", "configure",
            "--agent", "a",
            "--memory-root", str(tmp_path),
            "--agent-identity-text", "I am a growth hacker.",
        ])
        assert result == 0
        out = json.loads(capsys.readouterr().out)
        assert "agent_identity" in out["updated"]

    def test_configure_sets_additional_prompt_text(self, tmp_path, capsys):
        _run(["outreach", "prepare", "--agent", "a", "--memory-root", str(tmp_path)])
        capsys.readouterr()

        _run([
            "outreach", "configure",
            "--agent", "a",
            "--memory-root", str(tmp_path),
            "--additional-prompt-text", "Keep emails under 80 words.",
        ])
        out = json.loads(capsys.readouterr().out)
        assert "additional_prompt" in out["updated"]

    def test_configure_runtime_param_max_tokens(self, tmp_path, capsys):
        _run(["outreach", "prepare", "--agent", "a", "--memory-root", str(tmp_path)])
        capsys.readouterr()

        _run([
            "outreach", "configure",
            "--agent", "a",
            "--memory-root", str(tmp_path),
            "--runtime-param", "max_tokens=50000",
        ])
        out = json.loads(capsys.readouterr().out)
        assert "runtime_parameters" in out["updated"]
        assert out["query_config"]["max_tokens"] == 50000

    def test_configure_runtime_param_reset_threshold(self, tmp_path, capsys):
        _run(["outreach", "prepare", "--agent", "a", "--memory-root", str(tmp_path)])
        capsys.readouterr()

        _run([
            "outreach", "configure",
            "--agent", "a",
            "--memory-root", str(tmp_path),
            "--runtime-param", "reset_threshold=0.75",
        ])
        out = json.loads(capsys.readouterr().out)
        assert out["query_config"]["reset_threshold"] == pytest.approx(0.75)

    def test_configure_query_from_file(self, tmp_path, capsys):
        query_file = tmp_path / "query.txt"
        query_file.write_text("CTOs at seed-stage startups", encoding="utf-8")

        _run(["outreach", "prepare", "--agent", "a", "--memory-root", str(tmp_path)])
        capsys.readouterr()

        _run([
            "outreach", "configure",
            "--agent", "a",
            "--memory-root", str(tmp_path),
            "--query-file", str(query_file),
        ])
        out = json.loads(capsys.readouterr().out)
        assert out["query_config"]["search_query"] == "CTOs at seed-stage startups"

    def test_configure_additional_prompt_from_file(self, tmp_path, capsys):
        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text("Be brief.", encoding="utf-8")

        _run(["outreach", "prepare", "--agent", "a", "--memory-root", str(tmp_path)])
        capsys.readouterr()

        _run([
            "outreach", "configure",
            "--agent", "a",
            "--memory-root", str(tmp_path),
            "--additional-prompt-file", str(prompt_file),
        ])
        out = json.loads(capsys.readouterr().out)
        assert "additional_prompt" in out["updated"]

    def test_configure_no_args_updates_nothing(self, tmp_path, capsys):
        _run(["outreach", "prepare", "--agent", "a", "--memory-root", str(tmp_path)])
        capsys.readouterr()

        _run(["outreach", "configure", "--agent", "a", "--memory-root", str(tmp_path)])
        out = json.loads(capsys.readouterr().out)
        assert out["updated"] == []
        assert out["status"] == "configured"


# ---------------------------------------------------------------------------
# show command
# ---------------------------------------------------------------------------


class TestShowCommand:
    def test_show_emits_valid_json(self, tmp_path, capsys):
        _run(["outreach", "prepare", "--agent", "a", "--memory-root", str(tmp_path)])
        capsys.readouterr()

        result = _run(["outreach", "show", "--agent", "a", "--memory-root", str(tmp_path)])
        assert result == 0
        out = json.loads(capsys.readouterr().out)
        assert "query_config" in out
        assert "memory_path" in out
        assert "run_files" in out

    def test_show_after_configure_reflects_query(self, tmp_path, capsys):
        _run(["outreach", "prepare", "--agent", "a", "--memory-root", str(tmp_path)])
        _run([
            "outreach", "configure",
            "--agent", "a",
            "--memory-root", str(tmp_path),
            "--query-text", "Heads of Product",
        ])
        capsys.readouterr()

        _run(["outreach", "show", "--agent", "a", "--memory-root", str(tmp_path)])
        out = json.loads(capsys.readouterr().out)
        assert out["query_config"]["search_query"] == "Heads of Product"


# ---------------------------------------------------------------------------
# normalize_exa_outreach_runtime_parameters
# ---------------------------------------------------------------------------


class TestNormalizeRuntimeParameters:
    def test_max_tokens_coerced_to_int(self):
        result = normalize_exa_outreach_runtime_parameters({"max_tokens": "60000"})
        assert result["max_tokens"] == 60000
        assert isinstance(result["max_tokens"], int)

    def test_reset_threshold_coerced_to_float(self):
        result = normalize_exa_outreach_runtime_parameters({"reset_threshold": "0.8"})
        assert result["reset_threshold"] == pytest.approx(0.8)
        assert isinstance(result["reset_threshold"], float)

    def test_unsupported_key_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            normalize_exa_outreach_runtime_parameters({"bad_key": "1"})

    def test_empty_dict_returns_empty(self):
        assert normalize_exa_outreach_runtime_parameters({}) == {}

    def test_both_params_at_once(self):
        result = normalize_exa_outreach_runtime_parameters(
            {"max_tokens": 50000, "reset_threshold": 0.85}
        )
        assert result["max_tokens"] == 50000
        assert result["reset_threshold"] == pytest.approx(0.85)

    def test_boolean_max_tokens_raises(self):
        with pytest.raises(ValueError):
            normalize_exa_outreach_runtime_parameters({"max_tokens": True})

    def test_boolean_reset_threshold_raises(self):
        with pytest.raises(ValueError):
            normalize_exa_outreach_runtime_parameters({"reset_threshold": False})


# ---------------------------------------------------------------------------
# SUPPORTED_EXA_OUTREACH_RUNTIME_PARAMETERS constant
# ---------------------------------------------------------------------------


class TestSupportedParameters:
    def test_contains_max_tokens(self):
        assert "max_tokens" in SUPPORTED_EXA_OUTREACH_RUNTIME_PARAMETERS

    def test_contains_reset_threshold(self):
        assert "reset_threshold" in SUPPORTED_EXA_OUTREACH_RUNTIME_PARAMETERS


# ---------------------------------------------------------------------------
# run command (factory loading)
# ---------------------------------------------------------------------------


class TestRunCommand:
    def test_run_invokes_agent(self, tmp_path, capsys):
        from harnessiq.shared.exa_outreach import ExaOutreachMemoryStore

        # Prepare memory
        _run(["outreach", "prepare", "--agent", "a", "--memory-root", str(tmp_path)])
        _run([
            "outreach", "configure",
            "--agent", "a",
            "--memory-root", str(tmp_path),
            "--query-text", "VPs of Engineering",
        ])
        capsys.readouterr()

        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.cycles_completed = 1
        mock_result.pause_reason = "done"
        mock_result.resets = 0
        mock_result.status = "completed"
        mock_agent.run.return_value = mock_result
        mock_agent._current_run_id = "run_1"

        mock_model = MagicMock()
        mock_exa_creds = MagicMock()
        mock_resend_creds = MagicMock()
        mock_email_data = [
            {"id": "t1", "title": "T", "subject": "S", "description": "D", "actual_email": "Body"}
        ]

        with (
            patch(
                "harnessiq.cli.common.load_factory",
                return_value=lambda: mock_model,
            ),
            patch(
                "harnessiq.cli.runners.exa_outreach.load_factory",
                side_effect=[
                    lambda: mock_exa_creds,
                    lambda: mock_resend_creds,
                    lambda: mock_email_data,
                ],
            ),
            patch(
                "harnessiq.cli.runners.exa_outreach.ExaOutreachAgent",
                return_value=mock_agent,
            ),
        ):
            result = _run([
                "outreach", "run",
                "--agent", "a",
                "--memory-root", str(tmp_path),
                "--model-factory", "mod:model",
                "--exa-credentials-factory", "mod:exa",
                "--resend-credentials-factory", "mod:resend",
                "--email-data-factory", "mod:emails",
            ])

        assert result == 0
        # _handle_run prints a human-readable summary before emitting JSON;
        # extract the last JSON object from stdout
        stdout = capsys.readouterr().out
        json_start = stdout.find("{")
        out = json.loads(stdout[json_start:])
        assert out["run_id"] == "run_1"
        assert out["result"]["cycles_completed"] == 1

    def test_run_bad_model_factory_raises(self, tmp_path, capsys):
        _run(["outreach", "prepare", "--agent", "a", "--memory-root", str(tmp_path)])
        capsys.readouterr()

        mock_model_no_generate = object()

        with (
            patch(
                "harnessiq.cli.common.load_factory",
                return_value=lambda: mock_model_no_generate,
            ),
            patch(
                "harnessiq.cli.runners.exa_outreach.load_factory",
                side_effect=[
                    lambda: MagicMock(),
                    lambda: MagicMock(),
                    lambda: [],
                ],
            ),
        ):
            with pytest.raises(TypeError, match="generate_turn"):
                _run([
                    "outreach", "run",
                    "--agent", "a",
                    "--memory-root", str(tmp_path),
                    "--model-factory", "mod:model",
                    "--exa-credentials-factory", "mod:exa",
                    "--resend-credentials-factory", "mod:resend",
                    "--email-data-factory", "mod:emails",
                ])

    def test_run_non_list_email_factory_raises(self, tmp_path, capsys):
        _run(["outreach", "prepare", "--agent", "a", "--memory-root", str(tmp_path)])
        capsys.readouterr()

        mock_model = MagicMock()

        with (
            patch(
                "harnessiq.cli.common.load_factory",
                return_value=lambda: mock_model,
            ),
            patch(
                "harnessiq.cli.runners.exa_outreach.load_factory",
                side_effect=[
                    lambda: MagicMock(),
                    lambda: MagicMock(),
                    lambda: "not-a-list",
                ],
            ),
        ):
            with pytest.raises(TypeError, match="list"):
                _run([
                    "outreach", "run",
                    "--agent", "a",
                    "--memory-root", str(tmp_path),
                    "--model-factory", "mod:model",
                    "--exa-credentials-factory", "mod:exa",
                    "--resend-credentials-factory", "mod:resend",
                    "--email-data-factory", "mod:emails",
                ])
