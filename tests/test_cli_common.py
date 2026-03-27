from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from harnessiq.cli.adapters.utils.factories import (
    load_factory_assignment_map,
    load_optional_iterable_factory,
)
from harnessiq.cli.common import (
    add_agent_options,
    add_model_selection_options,
    add_text_or_file_options,
    emit_json,
    parse_generic_assignments,
    parse_scalar,
    resolve_agent_model,
    resolve_memory_path,
    resolve_text_argument,
    slugify_agent_name,
    split_assignment,
)
from harnessiq.config import ModelProfile, ModelProfileStore


class _Model:
    def generate_turn(self, request):  # pragma: no cover - behavior is irrelevant here
        del request
        return None


class _FakeIterableFactoryLoader:
    def __init__(self) -> None:
        self.loaded_specs: list[str] = []

    def __call__(self, spec: str):
        self.loaded_specs.append(spec)

        def factory() -> tuple[str, str]:
            return (spec, spec.upper())

        return factory


class _FakeAssignmentFactoryLoader:
    def __init__(self) -> None:
        self.loaded_specs: list[str] = []

    def __call__(self, spec: str):
        self.loaded_specs.append(spec)

        def factory() -> dict[str, str]:
            return {"spec": spec}

        return factory


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


def test_load_optional_iterable_factory_accepts_injected_loader_contract() -> None:
    loader = _FakeIterableFactoryLoader()

    created = load_optional_iterable_factory(
        "tests.test_cli_common:create_tools",
        factory_loader=loader,
    )

    assert created == (
        "tests.test_cli_common:create_tools",
        "TESTS.TEST_CLI_COMMON:CREATE_TOOLS",
    )
    assert loader.loaded_specs == ["tests.test_cli_common:create_tools"]


def test_load_factory_assignment_map_accepts_injected_loader_contract() -> None:
    loader = _FakeAssignmentFactoryLoader()

    created = load_factory_assignment_map(
        ["search=tests.test_cli_common:create_search", "crm=tests.test_cli_common:create_crm"],
        factory_loader=loader,
    )

    assert created == {
        "search": {"spec": "tests.test_cli_common:create_search"},
        "crm": {"spec": "tests.test_cli_common:create_crm"},
    }
    assert loader.loaded_specs == [
        "tests.test_cli_common:create_search",
        "tests.test_cli_common:create_crm",
    ]


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


def test_add_model_selection_options_registers_expected_flags() -> None:
    parser = argparse.ArgumentParser()
    add_model_selection_options(parser)
    args = parser.parse_args(["--model", "openai:gpt-5.4"])
    assert args.model == "openai:gpt-5.4"
    assert args.model_profile is None
    assert args.model_factory is None


def test_resolve_agent_model_requires_exactly_one_selection() -> None:
    with pytest.raises(ValueError, match="Exactly one"):
        resolve_agent_model()
    with pytest.raises(ValueError, match="Exactly one"):
        resolve_agent_model(model_factory="a:b", model_spec="openai:gpt-5.4")


def test_resolve_agent_model_uses_model_spec() -> None:
    model = _Model()
    with patch("harnessiq.cli.common.create_model_from_spec", return_value=model) as patched:
        resolved = resolve_agent_model(model_spec="openai:gpt-5.4")
    assert resolved is model
    patched.assert_called_once_with("openai:gpt-5.4")


def test_resolve_agent_model_uses_profile_lookup(tmp_path: Path) -> None:
    profile = ModelProfile(
        name="work",
        provider="grok",
        model_name="grok-4-1-fast-reasoning",
        reasoning_effort="high",
    )
    ModelProfileStore(home_dir=tmp_path).upsert(profile)

    resolved_model = _Model()
    with patch("harnessiq.cli.common.create_model_from_profile", return_value=resolved_model) as patched:
        resolved = resolve_agent_model(profile_name="work", home_dir=tmp_path)

    assert resolved is resolved_model
    patched.assert_called_once()
    assert patched.call_args.args[0].as_dict() == profile.as_dict()


def test_resolve_agent_model_rejects_non_agent_model() -> None:
    with patch("harnessiq.cli.common.create_model_from_spec", return_value=object()):
        with pytest.raises(TypeError, match="generate_turn"):
            resolve_agent_model(model_spec="openai:gpt-5.4")
