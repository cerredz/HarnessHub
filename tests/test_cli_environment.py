from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from harnessiq.cli._langsmith import seed_cli_environment


def test_seed_cli_environment_reads_dot_env_when_local_env_is_absent(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("XAI_API_KEY=dot-env-key\n", encoding="utf-8")

    with patch.dict(os.environ, {}, clear=True):
        applied = seed_cli_environment(tmp_path)

        assert applied["XAI_API_KEY"] == "dot-env-key"
        assert os.environ["XAI_API_KEY"] == "dot-env-key"


def test_seed_cli_environment_uses_local_env_as_overlay(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("XAI_API_KEY=base-key\n", encoding="utf-8")
    (tmp_path / "local.env").write_text("XAI_API_KEY=local-key\n", encoding="utf-8")

    with patch.dict(os.environ, {}, clear=True):
        applied = seed_cli_environment(tmp_path)

        assert applied["XAI_API_KEY"] == "local-key"
        assert os.environ["XAI_API_KEY"] == "local-key"


def test_seed_cli_environment_preserves_existing_shell_env(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("XAI_API_KEY=file-key\n", encoding="utf-8")

    with patch.dict(os.environ, {"XAI_API_KEY": "shell-key"}, clear=True):
        applied = seed_cli_environment(tmp_path)
        assert "XAI_API_KEY" not in applied
        assert os.environ["XAI_API_KEY"] == "shell-key"


def test_seed_cli_environment_backfills_langsmith_aliases(tmp_path: Path) -> None:
    (tmp_path / "local.env").write_text(
        "LANGCHAIN_API_KEY=langchain-key\nLANGCHAIN_PROJECT=langchain-project\n",
        encoding="utf-8",
    )

    with patch.dict(os.environ, {}, clear=True):
        seed_cli_environment(tmp_path)

        assert os.environ["LANGSMITH_API_KEY"] == "langchain-key"
        assert os.environ["LANGCHAIN_API_KEY"] == "langchain-key"
        assert os.environ["LANGSMITH_PROJECT"] == "langchain-project"
        assert os.environ["LANGCHAIN_PROJECT"] == "langchain-project"
