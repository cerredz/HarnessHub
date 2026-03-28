"""Tests for the provider catalog CLI commands."""

from __future__ import annotations

import json

from harnessiq.cli.main import build_parser, main


def _run(argv: list[str]) -> int:
    return main(argv)


def test_providers_subcommand_registered() -> None:
    parser = build_parser()
    args, _ = parser.parse_known_args(["providers", "list"])
    assert args.providers_command == "list"


def test_providers_list_emits_provider_catalog_json(capsys) -> None:
    result = _run(["providers", "list"])
    assert result == 0

    payload = json.loads(capsys.readouterr().out)
    families = {provider["family"] for provider in payload["providers"]}
    assert "creatify" in families
    assert "serper" in families


def test_providers_show_emits_family_details(capsys) -> None:
    result = _run(["providers", "show", "creatify"])
    assert result == 0

    payload = json.loads(capsys.readouterr().out)
    provider = payload["provider"]
    assert provider["family"] == "creatify"
    assert "creatify.request" in provider["tool_keys"]
    assert any(field["name"] == "api_key" for field in provider["credential_fields"])
