"""Tests for the master prompt CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harnessiq.cli.main import build_parser, main


def _run(argv: list[str]) -> int:
    return main(argv)


class TestMasterPromptParserRegistration:
    def test_prompts_subcommand_registered(self) -> None:
        parser = build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["prompts", "--help"])
        assert exc_info.value.code == 0

    def test_prompts_list_subcommand_registered(self) -> None:
        parser = build_parser()
        args, _ = parser.parse_known_args(["prompts", "list"])
        assert args.prompts_command == "list"

    def test_prompts_show_subcommand_registered(self) -> None:
        parser = build_parser()
        args, _ = parser.parse_known_args(["prompts", "show", "create_master_prompts"])
        assert args.prompts_command == "show"

    def test_prompts_search_subcommand_registered(self) -> None:
        parser = build_parser()
        args, _ = parser.parse_known_args(["prompts", "search", "master"])
        assert args.prompts_command == "search"

    def test_prompts_text_subcommand_registered(self) -> None:
        parser = build_parser()
        args, _ = parser.parse_known_args(["prompts", "text", "create_master_prompts"])
        assert args.prompts_command == "text"

    def test_prompts_activate_subcommand_registered(self) -> None:
        parser = build_parser()
        args, _ = parser.parse_known_args(["prompts", "activate", "create_master_prompts"])
        assert args.prompts_command == "activate"

    def test_prompts_current_subcommand_registered(self) -> None:
        parser = build_parser()
        args, _ = parser.parse_known_args(["prompts", "current"])
        assert args.prompts_command == "current"

    def test_prompts_clear_subcommand_registered(self) -> None:
        parser = build_parser()
        args, _ = parser.parse_known_args(["prompts", "clear"])
        assert args.prompts_command == "clear"


class TestMasterPromptCommands:
    def test_list_emits_prompt_catalog_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = _run(["prompts", "list"])
        assert result == 0

        payload = json.loads(capsys.readouterr().out)
        assert payload["count"] >= 1
        assert "create_master_prompts" in payload["keys"]
        assert any(prompt["key"] == "create_master_prompts" for prompt in payload["prompts"])

    def test_show_emits_full_prompt_payload(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = _run(["prompts", "show", "create_master_prompts"])
        assert result == 0

        payload = json.loads(capsys.readouterr().out)
        assert payload["prompt"]["key"] == "create_master_prompts"
        assert payload["prompt"]["title"]
        assert payload["prompt"]["description"]
        assert payload["prompt"]["prompt"]

    def test_text_prints_raw_prompt(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = _run(["prompts", "text", "create_master_prompts"])
        assert result == 0

        output = capsys.readouterr().out
        assert "Identity" in output
        assert "Goal" in output

    def test_show_unknown_prompt_raises_key_error(self) -> None:
        with pytest.raises(KeyError):
            _run(["prompts", "show", "does_not_exist"])

    def test_search_filters_prompt_catalog(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = _run(["prompts", "search", "master"])
        assert result == 0

        payload = json.loads(capsys.readouterr().out)
        assert payload["count"] >= 1
        assert all(
            "master" in prompt["key"].lower()
            or "master" in prompt["title"].lower()
            or "master" in prompt["description"].lower()
            for prompt in payload["prompts"]
        )

    def test_activate_emits_active_prompt_payload_and_writes_files(
        self,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
    ) -> None:
        result = _run(["prompts", "activate", "create_master_prompts", "--repo-root", str(tmp_path)])
        assert result == 0

        payload = json.loads(capsys.readouterr().out)
        assert payload["active"] is True
        assert payload["prompt"]["key"] == "create_master_prompts"
        assert Path(payload["files"]["claude"]).exists()
        assert Path(payload["files"]["codex"]).exists()
        assert Path(payload["files"]["state"]).exists()

    def test_current_reports_inactive_state_when_no_prompt_is_active(
        self,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
    ) -> None:
        result = _run(["prompts", "current", "--repo-root", str(tmp_path)])
        assert result == 0

        payload = json.loads(capsys.readouterr().out)
        assert payload["active"] is False
        assert payload["prompt"] is None

    def test_current_reports_active_prompt_after_activation(
        self,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
    ) -> None:
        assert _run(["prompts", "activate", "create_master_prompts", "--repo-root", str(tmp_path)]) == 0
        capsys.readouterr()

        result = _run(["prompts", "current", "--repo-root", str(tmp_path)])
        assert result == 0

        payload = json.loads(capsys.readouterr().out)
        assert payload["active"] is True
        assert payload["prompt"]["key"] == "create_master_prompts"

    def test_clear_removes_active_prompt_files(
        self,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
    ) -> None:
        assert _run(["prompts", "activate", "create_master_prompts", "--repo-root", str(tmp_path)]) == 0
        capsys.readouterr()

        result = _run(["prompts", "clear", "--repo-root", str(tmp_path)])
        assert result == 0

        payload = json.loads(capsys.readouterr().out)
        assert payload["active"] is False
        assert not (tmp_path / ".claude" / "CLAUDE.md").exists()
        assert not (tmp_path / "AGENTS.override.md").exists()

    def test_activate_resolves_to_nearest_git_root(
        self,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
    ) -> None:
        repo_root = tmp_path / "repo"
        nested = repo_root / "services" / "api"
        nested.mkdir(parents=True)
        (repo_root / ".git").write_text("gitdir: fake\n", encoding="utf-8")

        result = _run(["prompts", "activate", "create_master_prompts", "--repo-root", str(nested)])
        assert result == 0

        payload = json.loads(capsys.readouterr().out)
        assert Path(payload["files"]["claude"]) == repo_root / ".claude" / "CLAUDE.md"
        assert Path(payload["files"]["codex"]) == repo_root / "AGENTS.override.md"
