"""Tests for the master prompt CLI commands."""

from __future__ import annotations

import json

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

    def test_prompts_text_subcommand_registered(self) -> None:
        parser = build_parser()
        args, _ = parser.parse_known_args(["prompts", "text", "create_master_prompts"])
        assert args.prompts_command == "text"


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
