"""Helpers for activating one bundled master prompt as project session context."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from harnessiq.master_prompts import get_prompt

_CLAUDE_FILE = Path(".claude") / "CLAUDE.md"
_CODEX_FILE = Path("AGENTS.override.md")
_STATE_FILE = Path(".harnessiq") / "master_prompt_session" / "active_prompt.json"
_GENERATOR_HINT = "harnessiq prompts activate <prompt-key>"
_BLOCK_BEGIN = "<!-- HARNESSIQ_MASTER_PROMPT_SESSION:BEGIN -->"
_BLOCK_END = "<!-- HARNESSIQ_MASTER_PROMPT_SESSION:END -->"
_BLOCK_PATTERN = re.compile(
    rf"{re.escape(_BLOCK_BEGIN)}.*?{re.escape(_BLOCK_END)}\n?",
    flags=re.DOTALL,
)


@dataclass(frozen=True, slots=True)
class PromptSessionActivation:
    """Resolved metadata for one active project-scoped master prompt."""

    repo_root: Path
    key: str
    title: str
    description: str
    claude_path: Path
    codex_path: Path
    state_path: Path

    def to_payload(self) -> dict[str, object]:
        """Return a deterministic JSON-serializable payload."""
        return {
            "active": True,
            "prompt": {
                "key": self.key,
                "title": self.title,
                "description": self.description,
            },
            "files": {
                "claude": self.claude_path,
                "codex": self.codex_path,
                "state": self.state_path,
            },
        }


def activate_prompt_session(prompt_key: str, *, repo_root: str | Path) -> PromptSessionActivation:
    """Write project instruction overlays for the selected bundled prompt."""
    root = Path(repo_root).expanduser().resolve()
    prompt = get_prompt(prompt_key)
    paths = _PromptSessionPaths.for_repo(root)

    _write_text(paths.claude_path, _render_claude_document(prompt.key, prompt.title, prompt.description, prompt.prompt))
    _write_text(paths.codex_path, _render_codex_document(prompt.key, prompt.title, prompt.description, prompt.prompt))
    _write_state(
        paths.state_path,
        {
            "prompt": {
                "key": prompt.key,
                "title": prompt.title,
                "description": prompt.description,
            }
        },
    )
    return PromptSessionActivation(
        repo_root=root,
        key=prompt.key,
        title=prompt.title,
        description=prompt.description,
        claude_path=paths.claude_path,
        codex_path=paths.codex_path,
        state_path=paths.state_path,
    )


def get_active_prompt_session(*, repo_root: str | Path) -> PromptSessionActivation | None:
    """Return the currently active project prompt, if any."""
    root = Path(repo_root).expanduser().resolve()
    paths = _PromptSessionPaths.for_repo(root)
    if not paths.state_path.exists():
        return None
    payload = json.loads(paths.state_path.read_text(encoding="utf-8"))
    prompt_payload = payload.get("prompt")
    if not isinstance(prompt_payload, dict):
        return None
    key = str(prompt_payload.get("key", "")).strip()
    title = str(prompt_payload.get("title", "")).strip()
    description = str(prompt_payload.get("description", "")).strip()
    if not key or not title or not description:
        return None
    return PromptSessionActivation(
        repo_root=root,
        key=key,
        title=title,
        description=description,
        claude_path=paths.claude_path,
        codex_path=paths.codex_path,
        state_path=paths.state_path,
    )


def clear_prompt_session(*, repo_root: str | Path) -> dict[str, object]:
    """Remove generated project overlays and local active-state metadata."""
    root = Path(repo_root).expanduser().resolve()
    paths = _PromptSessionPaths.for_repo(root)
    removed: list[Path] = []
    for path in (paths.claude_path, paths.codex_path):
        if _remove_generated_block(path):
            removed.append(path)
    if paths.state_path.exists():
        paths.state_path.unlink()
        removed.append(paths.state_path)
    _remove_empty_parent(paths.claude_path.parent, stop=root)
    _remove_empty_parent(paths.state_path.parent, stop=root)
    return {
        "active": False,
        "removed_files": removed,
        "files": {
            "claude": paths.claude_path,
            "codex": paths.codex_path,
            "state": paths.state_path,
        },
    }


@dataclass(frozen=True, slots=True)
class _PromptSessionPaths:
    repo_root: Path
    claude_path: Path
    codex_path: Path
    state_path: Path

    @classmethod
    def for_repo(cls, repo_root: Path) -> _PromptSessionPaths:
        return cls(
            repo_root=repo_root,
            claude_path=repo_root / _CLAUDE_FILE,
            codex_path=repo_root / _CODEX_FILE,
            state_path=repo_root / _STATE_FILE,
        )


def _write_state(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _remove_empty_parent(path: Path, *, stop: Path) -> None:
    current = path
    stop = stop.resolve()
    while current != stop:
        if current.exists() and any(current.iterdir()):
            return
        if current.exists():
            current.rmdir()
        current = current.parent


def _render_claude_document(key: str, title: str, description: str, prompt_text: str) -> str:
    return _render_instruction_document(
        platform_name="Claude Code",
        instruction_file=".claude/CLAUDE.md",
        key=key,
        title=title,
        description=description,
        prompt_text=prompt_text,
    )


def _render_codex_document(key: str, title: str, description: str, prompt_text: str) -> str:
    return _render_instruction_document(
        platform_name="Codex",
        instruction_file="AGENTS.override.md",
        key=key,
        title=title,
        description=description,
        prompt_text=prompt_text,
    )


def _render_instruction_document(
    *,
    platform_name: str,
    instruction_file: str,
    key: str,
    title: str,
    description: str,
    prompt_text: str,
) -> str:
    lines = [
        _BLOCK_BEGIN,
        f"# Generated {platform_name} Master Prompt Context",
        "",
        f"This file is generated by `{_GENERATOR_HINT}`. Do not hand-edit it.",
        "",
        "Apply the active master prompt below as always-on project guidance for every request in this repository session unless the user explicitly overrides it.",
        "",
        "## Active Prompt",
        "",
        f"- Key: `{key}`",
        f"- Title: {title}",
        f"- Description: {description}",
        f"- Instruction file: `{instruction_file}`",
        "",
        "## Active Master Prompt",
        "",
        prompt_text.strip(),
        "",
        _BLOCK_END,
        "",
    ]
    return "\n".join(lines)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(_merge_generated_block(existing, content), encoding="utf-8")


def _merge_generated_block(existing: str, generated_block: str) -> str:
    if _BLOCK_BEGIN in existing and _BLOCK_END in existing:
        merged = _BLOCK_PATTERN.sub(generated_block, existing, count=1)
    elif existing.strip():
        merged = existing.rstrip() + "\n\n" + generated_block
    else:
        merged = generated_block
    return merged.rstrip() + "\n"


def _remove_generated_block(path: Path) -> bool:
    if not path.exists():
        return False
    existing = path.read_text(encoding="utf-8")
    if _BLOCK_BEGIN not in existing or _BLOCK_END not in existing:
        return False
    cleaned = _BLOCK_PATTERN.sub("", existing, count=1).strip()
    if cleaned:
        path.write_text(cleaned + "\n", encoding="utf-8")
        return True
    path.unlink()
    return True


__all__ = [
    "PromptSessionActivation",
    "activate_prompt_session",
    "clear_prompt_session",
    "get_active_prompt_session",
]
