from __future__ import annotations

import io
import json
import os
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from harnessiq.cli.main import build_parser, main
from harnessiq.config import ModelProfile, ModelProfileStore


def _run(argv: list[str]) -> tuple[int, dict[str, object]]:
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        exit_code = main(argv)
    return exit_code, json.loads(stdout.getvalue())


def test_model_profile_store_round_trip(tmp_path: Path) -> None:
    store = ModelProfileStore(home_dir=tmp_path)
    config_path = store.upsert(
        ModelProfile(
            name="work",
            provider="openai",
            model_name="gpt-5.4",
            temperature=0.2,
            max_output_tokens=2048,
        )
    )

    assert config_path == tmp_path / "models.json"
    catalog = store.load()
    assert [profile.name for profile in catalog.profiles] == ["work"]
    assert catalog.profile_for("work").as_dict() == {
        "max_output_tokens": 2048,
        "model_name": "gpt-5.4",
        "name": "work",
        "provider": "openai",
        "temperature": 0.2,
    }


def test_models_subcommand_registered() -> None:
    parser = build_parser()
    args, _ = parser.parse_known_args(["models", "list"])
    assert args.models_command == "list"


def test_models_cli_add_and_list_round_trip(tmp_path: Path) -> None:
    with patch.dict(os.environ, {"HARNESSIQ_HOME": str(tmp_path)}):
        exit_code, added = _run(
            [
                "models",
                "add",
                "--name",
                "work",
                "--model",
                "grok:grok-4-1-fast-reasoning",
                "--reasoning-effort",
                "high",
                "--max-output-tokens",
                "4096",
            ]
        )
        assert exit_code == 0
        assert added["status"] == "saved"
        assert Path(str(added["config_path"])) == tmp_path.resolve() / "models.json"
        assert added["profile"] == {
            "max_output_tokens": 4096,
            "model_name": "grok-4-1-fast-reasoning",
            "name": "work",
            "provider": "grok",
            "reasoning_effort": "high",
        }

        exit_code, listed = _run(["models", "list"])
        assert exit_code == 0
        assert listed["profiles"] == [added["profile"]]


def test_models_show_remove_validate_import_and_export(tmp_path: Path) -> None:
    import_path = tmp_path / "profiles.json"
    export_path = tmp_path / "export.json"
    import_path.write_text(
        json.dumps(
            [
                {
                    "name": "team",
                    "provider": "anthropic",
                    "model_name": "claude-sonnet-4-5",
                    "temperature": 0.1,
                }
            ]
        ),
        encoding="utf-8",
    )

    with patch.dict(os.environ, {"HARNESSIQ_HOME": str(tmp_path)}):
        added_exit_code, _ = _run(
            [
                "models",
                "add",
                "--name",
                "work",
                "--model",
                "openai:gpt-5.4",
            ]
        )
        assert added_exit_code == 0

        show_exit_code, shown = _run(["models", "show", "work"])
        assert show_exit_code == 0
        assert shown["profile"]["name"] == "work"

        validate_exit_code, validated = _run(["models", "validate", "anthropic:claude-sonnet-4-5"])
        assert validate_exit_code == 0
        assert validated["valid"] is True
        assert validated["provider"] == "anthropic"

        import_exit_code, imported = _run(["models", "import", str(import_path)])
        assert import_exit_code == 0
        assert imported["profile_count"] == 2

        export_exit_code, exported = _run(["models", "export", "--output", str(export_path)])
        assert export_exit_code == 0
        assert exported["status"] == "exported"
        exported_profiles = json.loads(export_path.read_text(encoding="utf-8"))
        assert {profile["name"] for profile in exported_profiles} == {"team", "work"}

        remove_exit_code, removed = _run(["models", "remove", "work", "--confirm"])
        assert remove_exit_code == 0
        assert removed["status"] == "removed"
        remaining_profiles = ModelProfileStore(home_dir=tmp_path).load().profiles
        assert [profile.name for profile in remaining_profiles] == ["team"]


def test_models_validate_invalid_spec_returns_error_payload(capsys) -> None:
    result = main(["models", "validate", "not-a-spec"])
    assert result == 1

    payload = json.loads(capsys.readouterr().out)
    assert payload["valid"] is False
    assert payload["error"]


def test_models_remove_requires_confirm(tmp_path: Path) -> None:
    with patch.dict(os.environ, {"HARNESSIQ_HOME": str(tmp_path)}):
        _run(
            [
                "models",
                "add",
                "--name",
                "work",
                "--model",
                "openai:gpt-5.4",
            ]
        )

        with patch("sys.stdout", new=io.StringIO()):
            try:
                main(["models", "remove", "work"])
            except ValueError as exc:
                assert "--confirm" in str(exc)
            else:  # pragma: no cover - defensive
                raise AssertionError("Expected remove without --confirm to fail.")


def test_models_import_rejects_duplicate_profile_names(tmp_path: Path) -> None:
    import_path = tmp_path / "profiles.json"
    import_path.write_text(
        json.dumps(
            [
                {
                    "name": "team",
                    "provider": "openai",
                    "model_name": "gpt-5.4",
                },
                {
                    "name": "team",
                    "provider": "anthropic",
                    "model_name": "claude-sonnet-4-5",
                },
            ]
        ),
        encoding="utf-8",
    )

    with patch.dict(os.environ, {"HARNESSIQ_HOME": str(tmp_path)}):
        with patch("sys.stdout", new=io.StringIO()):
            try:
                main(["models", "import", str(import_path)])
            except ValueError as exc:
                assert "duplicate profile names" in str(exc)
            else:  # pragma: no cover - defensive
                raise AssertionError("Expected duplicate import names to fail.")
