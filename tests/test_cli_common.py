from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from harnessiq.cli.common import (
    add_agent_options,
    add_text_or_file_options,
    emit_json,
    parse_generic_assignments,
    parse_scalar,
    resolve_memory_path,
    resolve_text_argument,
    slugify_agent_name,
    split_assignment,
)


def test_slugify_agent_name_normalizes_whitespace_and_symbols() -> None:
    assert slugify_agent_name("  my agent!  ") == "my-agent"


def test_slugify_agent_name_rejects_blank_values() -> None:
    with pytest.raises(ValueError):
        slugify_agent_name("   ")


def test_resolve_memory_path_uses_default_slugifier() -> None:
    path = resolve_memory_path("My Agent", "memory/root")
    assert path == Path("memory/root") / "My-Agent"


def test_resolve_memory_path_accepts_custom_slugifier() -> None:
    path = resolve_memory_path(
        "My Agent",
        "memory/root",
        slugifier=lambda value: value.lower().replace(" ", "_"),
    )
    assert path == Path("memory/root") / "my_agent"


def test_resolve_text_argument_prefers_inline_text(tmp_path: Path) -> None:
    file_path = tmp_path / "value.txt"
    file_path.write_text("from-file", encoding="utf-8")
    assert resolve_text_argument("inline", str(file_path)) == "inline"


def test_resolve_text_argument_reads_utf8_file(tmp_path: Path) -> None:
    file_path = tmp_path / "value.txt"
    file_path.write_text("from-file", encoding="utf-8")
    assert resolve_text_argument(None, str(file_path)) == "from-file"


def test_split_assignment_returns_key_and_value() -> None:
    assert split_assignment("foo=bar") == ("foo", "bar")


def test_split_assignment_rejects_missing_separator() -> None:
    with pytest.raises(ValueError):
        split_assignment("foobar")


def test_parse_scalar_decodes_json_scalars() -> None:
    assert parse_scalar("123") == 123
    assert parse_scalar("true") is True
    assert parse_scalar('"value"') == "value"


def test_parse_generic_assignments_decodes_multiple_values() -> None:
    parsed = parse_generic_assignments(("count=3", 'name="alpha"', "enabled=true"))
    assert parsed == {"count": 3, "name": "alpha", "enabled": True}


def test_emit_json_serializes_paths(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    emit_json({"path": tmp_path / "artifact.json"})
    payload = json.loads(capsys.readouterr().out)
    assert payload["path"].endswith("artifact.json")


def test_emit_json_stringifies_unknown_leaf_values(capsys: pytest.CaptureFixture[str]) -> None:
    class CustomValue:
        def __str__(self) -> str:
            return "custom-value"

    emit_json({"value": CustomValue()})
    payload = json.loads(capsys.readouterr().out)
    assert payload["value"] == "custom-value"


def test_add_agent_options_registers_expected_flags() -> None:
    parser = argparse.ArgumentParser()
    add_agent_options(
        parser,
        agent_help="Agent help.",
        memory_root_default="memory/test",
        memory_root_help="Memory root help.",
    )
    args = parser.parse_args(["--agent", "sample"])
    assert args.agent == "sample"
    assert args.memory_root == "memory/test"


def test_add_text_or_file_options_registers_expected_flags() -> None:
    parser = argparse.ArgumentParser()
    add_text_or_file_options(parser, "agent_identity", "Agent identity")
    args = parser.parse_args(["--agent-identity-text", "inline"])
    assert args.agent_identity_text == "inline"
