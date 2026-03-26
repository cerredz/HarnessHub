"""Tests for project-scoped master prompt session injection helpers."""

from __future__ import annotations

import json
from pathlib import Path

from harnessiq.master_prompts.session_injection import (
    activate_prompt_session,
    clear_prompt_session,
    get_active_prompt_session,
)


def test_activate_prompt_session_writes_generated_instruction_files(tmp_path: Path) -> None:
    activation = activate_prompt_session("create_master_prompts", repo_root=tmp_path)

    assert activation.key == "create_master_prompts"
    assert activation.claude_path.exists()
    assert activation.codex_path.exists()
    assert activation.state_path.exists()

    claude_text = activation.claude_path.read_text(encoding="utf-8")
    codex_text = activation.codex_path.read_text(encoding="utf-8")
    assert "Apply the active master prompt below as always-on project guidance" in claude_text
    assert "Apply the active master prompt below as always-on project guidance" in codex_text
    assert "create_master_prompts" in claude_text
    assert "create_master_prompts" in codex_text
    assert "You are a world-class prompt engineer and AI systems architect." in claude_text
    assert "You are a world-class prompt engineer and AI systems architect." in codex_text

    state_payload = json.loads(activation.state_path.read_text(encoding="utf-8"))
    assert state_payload["prompt"]["key"] == "create_master_prompts"


def test_get_active_prompt_session_reads_local_state(tmp_path: Path) -> None:
    activate_prompt_session("create_master_prompts", repo_root=tmp_path)

    activation = get_active_prompt_session(repo_root=tmp_path)

    assert activation is not None
    assert activation.key == "create_master_prompts"
    assert activation.claude_path == tmp_path / ".claude" / "CLAUDE.md"
    assert activation.codex_path == tmp_path / "AGENTS.override.md"


def test_get_active_prompt_session_returns_none_when_inactive(tmp_path: Path) -> None:
    assert get_active_prompt_session(repo_root=tmp_path) is None


def test_clear_prompt_session_removes_generated_files_and_state(tmp_path: Path) -> None:
    activation = activate_prompt_session("create_master_prompts", repo_root=tmp_path)

    payload = clear_prompt_session(repo_root=tmp_path)

    assert payload["active"] is False
    removed_files = {Path(path) for path in payload["removed_files"]}
    assert activation.claude_path in removed_files
    assert activation.codex_path in removed_files
    assert activation.state_path in removed_files
    assert not activation.claude_path.exists()
    assert not activation.codex_path.exists()
    assert not activation.state_path.exists()


def test_clear_prompt_session_is_idempotent_when_nothing_is_active(tmp_path: Path) -> None:
    payload = clear_prompt_session(repo_root=tmp_path)

    assert payload["active"] is False
    assert payload["removed_files"] == []


def test_activate_preserves_existing_instruction_content_and_clear_removes_only_managed_block(tmp_path: Path) -> None:
    claude_path = tmp_path / ".claude" / "CLAUDE.md"
    codex_path = tmp_path / "AGENTS.override.md"
    claude_path.parent.mkdir(parents=True, exist_ok=True)
    claude_path.write_text("# Existing Claude guidance\n", encoding="utf-8")
    codex_path.write_text("# Existing Codex guidance\n", encoding="utf-8")

    activate_prompt_session("create_master_prompts", repo_root=tmp_path)

    claude_text = claude_path.read_text(encoding="utf-8")
    codex_text = codex_path.read_text(encoding="utf-8")
    assert "# Existing Claude guidance" in claude_text
    assert "# Existing Codex guidance" in codex_text
    assert "HARNESSIQ_MASTER_PROMPT_SESSION:BEGIN" in claude_text
    assert "HARNESSIQ_MASTER_PROMPT_SESSION:BEGIN" in codex_text

    clear_prompt_session(repo_root=tmp_path)

    assert claude_path.read_text(encoding="utf-8") == "# Existing Claude guidance\n"
    assert codex_path.read_text(encoding="utf-8") == "# Existing Codex guidance\n"
