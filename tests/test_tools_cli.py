"""Tests for the tool catalog CLI commands."""

from __future__ import annotations

import json

import pytest

from harnessiq.cli.main import build_parser, main


def _run(argv: list[str]) -> int:
    return main(argv)


def test_tools_subcommand_registered() -> None:
    parser = build_parser()
    args, _ = parser.parse_known_args(["tools", "list"])
    assert args.tools_command == "list"


def test_tools_list_emits_catalog_json(capsys: pytest.CaptureFixture[str]) -> None:
    result = _run(["tools", "list", "--family", "reason"])
    assert result == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] >= 1
    assert all(tool["family"] == "reason" for tool in payload["tools"])


def test_tools_show_emits_built_in_inspection_payload(capsys: pytest.CaptureFixture[str]) -> None:
    result = _run(["tools", "show", "reason.brainstorm"])
    assert result == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["tool"]["key"] == "reason.brainstorm"
    assert payload["tool"]["parameters"]
    assert payload["tool"]["function"]["module"]


def test_tools_show_emits_provider_payload_without_credentials(capsys: pytest.CaptureFixture[str]) -> None:
    result = _run(["tools", "show", "creatify.request"])
    assert result == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["tool"]["key"] == "creatify.request"
    assert payload["tool"]["required_parameters"] == ["operation"]
    operation = next(parameter for parameter in payload["tool"]["parameters"] if parameter["name"] == "operation")
    assert "enum" in operation["schema"]


def test_tools_families_emits_family_summaries(capsys: pytest.CaptureFixture[str]) -> None:
    result = _run(["tools", "families"])
    assert result == 0

    payload = json.loads(capsys.readouterr().out)
    families = {family["family"]: family for family in payload["families"]}
    assert "reason" in families
    assert "creatify" in families


def test_tools_validate_accepts_json_file(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "tool.json"
    path.write_text(
        json.dumps(
            {
                "key": "custom.shout",
                "description": "Convert text to uppercase.",
                "parameters": {"text": {"type": "string", "description": "Input text."}},
                "required": ["text"],
            }
        ),
        encoding="utf-8",
    )

    result = _run(["tools", "validate", str(path)])
    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["valid"] is True
    assert payload["tool"]["key"] == "custom.shout"


def test_tools_import_validate_only_reports_not_registered(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "tool.json"
    path.write_text(
        json.dumps(
            {
                "key": "custom.echo",
                "description": "Return the provided payload.",
                "parameters": {"payload": {"type": "object", "description": "Arbitrary payload."}},
            }
        ),
        encoding="utf-8",
    )

    result = _run(["tools", "import", str(path), "--validate-only"])
    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["valid"] is True
    assert payload["registered"] is False
