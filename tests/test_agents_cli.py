"""Tests for the agents manifest discovery CLI commands."""

from __future__ import annotations

import json

from harnessiq.cli.main import build_parser, main


def _run(argv: list[str]) -> int:
    return main(argv)


def test_agents_subcommand_registered() -> None:
    parser = build_parser()
    args, _ = parser.parse_known_args(["agents", "list"])
    assert args.agents_command == "list"


def test_agents_list_emits_registered_manifests(capsys) -> None:
    result = _run(["agents", "list"])
    assert result == 0

    payload = json.loads(capsys.readouterr().out)
    manifests = {agent["manifest_id"] for agent in payload["agents"]}
    assert "linkedin" in manifests
    assert "research_sweep" in manifests


def test_agents_show_matches_manifest_inspection_shape(capsys) -> None:
    result = _run(["agents", "show", "linkedin"])
    assert result == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["harness"] == "linkedin"
    assert payload["display_name"] == "LinkedIn Job Applier"
    assert "provider_credential_fields" in payload
