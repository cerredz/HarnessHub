"""Tests for the research sweep CLI commands."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from harnessiq.cli.main import build_parser, main
from harnessiq.providers.serper import SerperCredentials


def _run(argv: list[str]) -> int:
    return main(argv)


class TestParserRegistration:
    def test_research_sweep_subcommand_registered(self) -> None:
        parser = build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["research-sweep", "--help"])
        assert exc_info.value.code == 0

    def test_configure_subcommand_registered(self) -> None:
        parser = build_parser()
        args, _ = parser.parse_known_args(["research-sweep", "configure", "--agent", "sweep-a"])
        assert args.research_sweep_command == "configure"

    def test_run_subcommand_registered(self) -> None:
        parser = build_parser()
        args, _ = parser.parse_known_args(
            [
                "research-sweep",
                "run",
                "--agent",
                "sweep-a",
                "--model-factory",
                "mod:fn",
            ]
        )
        assert args.research_sweep_command == "run"


class TestConfigureAndShow:
    def test_prepare_and_configure_manage_memory(self, tmp_path, capsys) -> None:
        _run(["research-sweep", "prepare", "--agent", "sweep-a", "--memory-root", str(tmp_path)])
        capsys.readouterr()

        _run(
            [
                "research-sweep",
                "configure",
                "--agent",
                "sweep-a",
                "--memory-root",
                str(tmp_path),
                "--query-text",
                "mRNA vaccine efficacy",
                "--additional-prompt-text",
                "Focus on clinically relevant papers.",
                "--runtime-param",
                "max_tokens=64000",
                "--custom-param",
                "allowed_serper_operations=search,scholar",
            ]
        )
        configured = json.loads(capsys.readouterr().out)

        assert configured["status"] == "configured"
        assert configured["query"] == "mRNA vaccine efficacy"
        assert configured["runtime_parameters"]["max_tokens"] == 64000
        assert configured["custom_parameters"]["allowed_serper_operations"] == "search,scholar"
        assert "progress_reset" in configured["updated"]

        _run(["research-sweep", "show", "--agent", "sweep-a", "--memory-root", str(tmp_path)])
        shown = json.loads(capsys.readouterr().out)
        assert shown["query"] == "mRNA vaccine efficacy"
        assert shown["additional_prompt"] == "Focus on clinically relevant papers."


class TestRunCommand:
    def test_run_uses_supplied_serper_credentials_factory(self, tmp_path, capsys) -> None:
        _run(["research-sweep", "prepare", "--agent", "sweep-a", "--memory-root", str(tmp_path)])
        _run(
            [
                "research-sweep",
                "configure",
                "--agent",
                "sweep-a",
                "--memory-root",
                str(tmp_path),
                "--query-text",
                "few-shot learning for protein folding",
            ]
        )
        capsys.readouterr()

        mock_agent = MagicMock()
        mock_agent.instance_id = "instance-1"
        mock_agent.instance_name = "sweep-a"
        mock_agent.last_run_id = "ledger-1"
        mock_agent.run.return_value = MagicMock(
            cycles_completed=2,
            pause_reason=None,
            resets=0,
            status="completed",
        )

        with (
            patch(
                "harnessiq.cli.common.load_factory",
                return_value=lambda: MagicMock(),
            ),
            patch(
                "harnessiq.cli.runners.research_sweep.load_factory",
                return_value=lambda: SerperCredentials(api_key="cli-serper-key"),
            ),
            patch(
                "harnessiq.cli.runners.research_sweep.ResearchSweepAgent.from_memory",
                return_value=mock_agent,
            ) as patched_from_memory,
        ):
            result = _run(
                [
                    "research-sweep",
                    "run",
                    "--agent",
                    "sweep-a",
                    "--memory-root",
                    str(tmp_path),
                    "--model-factory",
                    "mod:model",
                    "--serper-credentials-factory",
                    "mod:serper",
                ]
            )

        assert result == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["result"]["status"] == "completed"
        assert payload["instance_name"] == "sweep-a"
        kwargs = patched_from_memory.call_args.kwargs
        assert kwargs["serper_credentials"].api_key == "cli-serper-key"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
