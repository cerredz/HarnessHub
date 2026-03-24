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
