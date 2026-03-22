"""Shared types, memory store, and constants for the Knowt agent harness."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harnessiq.shared.agents import DEFAULT_AGENT_MAX_TOKENS, DEFAULT_AGENT_RESET_THRESHOLD
from harnessiq.shared.harness_manifest import HarnessManifest, HarnessMemoryFileSpec, HarnessParameterSpec

# ---------------------------------------------------------------------------
# Filename constants
# ---------------------------------------------------------------------------

CURRENT_SCRIPT_FILENAME = "current_script.md"
CURRENT_AVATAR_DESCRIPTION_FILENAME = "current_avatar_description.md"
CREATION_LOG_FILENAME = "creation_log.jsonl"
PROMPTS_DIRNAME = "prompts"
MASTER_PROMPT_FILENAME = "master_prompt.md"


# ---------------------------------------------------------------------------
# KnowtCreationLogEntry
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class KnowtCreationLogEntry:
    """A single entry in the Knowt agent creation log."""

    timestamp: str
    action: str
    summary: str

    def as_dict(self) -> dict[str, str]:
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "KnowtCreationLogEntry":
        return cls(
            timestamp=str(payload["timestamp"]),
            action=str(payload["action"]),
            summary=str(payload["summary"]),
        )


# ---------------------------------------------------------------------------
# KnowtAgentConfig
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class KnowtAgentConfig:
    """Immutable configuration for a KnowtAgent instance."""

    memory_path: Path
    max_tokens: int = DEFAULT_AGENT_MAX_TOKENS
    reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD


# ---------------------------------------------------------------------------
# KnowtMemoryStore
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class KnowtMemoryStore:
    """File-backed memory store for the Knowt agent.

    Persists the current script, avatar description, and creation log
    to disk so state is durable across interrupted runs.
    """

    memory_path: Path

    def __post_init__(self) -> None:
        self.memory_path = Path(self.memory_path)

    # ------------------------------------------------------------------
    # Path properties
    # ------------------------------------------------------------------

    @property
    def current_script_path(self) -> Path:
        return self.memory_path / CURRENT_SCRIPT_FILENAME

    @property
    def current_avatar_description_path(self) -> Path:
        return self.memory_path / CURRENT_AVATAR_DESCRIPTION_FILENAME

    @property
    def creation_log_path(self) -> Path:
        return self.memory_path / CREATION_LOG_FILENAME

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def prepare(self) -> None:
        """Ensure the memory directory and required files exist."""
        self.memory_path.mkdir(parents=True, exist_ok=True)
        _ensure_text_file(self.current_script_path, "")
        _ensure_text_file(self.current_avatar_description_path, "")
        _ensure_text_file(self.creation_log_path, "")

    # ------------------------------------------------------------------
    # Script
    # ------------------------------------------------------------------

    def write_script(self, content: str) -> Path:
        """Persist the current script and return the file path."""
        return _write_text(self.current_script_path, content)

    def read_script(self) -> str | None:
        """Return the current script text, or None if not yet created."""
        content = _read_text(self.current_script_path)
        return content if content else None

    def is_script_created(self) -> bool:
        """Return True iff current_script.md exists and contains non-empty content."""
        return bool(_read_text(self.current_script_path))

    # ------------------------------------------------------------------
    # Avatar description
    # ------------------------------------------------------------------

    def write_avatar_description(self, content: str) -> Path:
        """Persist the current avatar description and return the file path."""
        return _write_text(self.current_avatar_description_path, content)

    def read_avatar_description(self) -> str | None:
        """Return the current avatar description, or None if not yet created."""
        content = _read_text(self.current_avatar_description_path)
        return content if content else None

    def is_avatar_description_created(self) -> bool:
        """Return True iff current_avatar_description.md exists and contains non-empty content."""
        return bool(_read_text(self.current_avatar_description_path))

    # ------------------------------------------------------------------
    # Creation log
    # ------------------------------------------------------------------

    def append_creation_log(self, entry: dict[str, Any]) -> None:
        """Append a creation log entry to creation_log.jsonl."""
        with self.creation_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True))
            handle.write("\n")

    def read_creation_log(self) -> list[KnowtCreationLogEntry]:
        """Return all creation log entries in chronological order."""
        return [
            KnowtCreationLogEntry.from_dict(json.loads(line))
            for line in self.creation_log_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ] if self.creation_log_path.exists() else []

    # ------------------------------------------------------------------
    # Generic file access (memory-directory-scoped)
    # ------------------------------------------------------------------

    def write_file(self, filename: str, content: str) -> Path:
        """Create or overwrite a file inside the memory directory."""
        target = self._safe_resolve(filename)
        return _write_text(target, content)

    def edit_file(self, filename: str, content: str) -> Path:
        """Overwrite the content of an existing file inside the memory directory."""
        target = self._safe_resolve(filename)
        return _write_text(target, content)

    def read_file(self, filename: str) -> str:
        """Read a file from the memory directory."""
        target = self._safe_resolve(filename)
        return target.read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _safe_resolve(self, filename: str) -> Path:
        """Resolve *filename* relative to memory_path and guard against traversal."""
        target = (self.memory_path / filename).resolve()
        root = self.memory_path.resolve()
        if target != root and root not in target.parents:
            message = f"File '{filename}' resolves outside the configured memory path."
            raise ValueError(message)
        return target


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _ensure_text_file(path: Path, default_content: str) -> None:
    if not path.exists():
        path.write_text(default_content, encoding="utf-8")


def _write_text(path: Path, content: str) -> Path:
    rendered = content if not content or content.endswith("\n") else f"{content}\n"
    path.write_text(rendered, encoding="utf-8")
    return path


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


KNOWT_HARNESS_MANIFEST = HarnessManifest(
    manifest_id="knowt",
    agent_name="knowt_content_creator",
    display_name="Knowt Content Creator",
    module_path="harnessiq.agents.knowt",
    class_name="KnowtAgent",
    cli_command=None,
    prompt_path="harnessiq/agents/knowt/prompts/master_prompt.md",
    runtime_parameters=(
        HarnessParameterSpec("max_tokens", "integer", "Maximum model context budget for the harness."),
        HarnessParameterSpec("reset_threshold", "number", "Fraction of max_tokens that triggers a reset."),
    ),
    memory_files=(
        HarnessMemoryFileSpec("current_script", CURRENT_SCRIPT_FILENAME, "Current generated script.", format="markdown"),
        HarnessMemoryFileSpec("current_avatar_description", CURRENT_AVATAR_DESCRIPTION_FILENAME, "Current generated avatar description.", format="markdown"),
        HarnessMemoryFileSpec("creation_log", CREATION_LOG_FILENAME, "Append-only creation pipeline log.", format="jsonl"),
    ),
    provider_families=("creatify",),
    output_schema={
        "type": "object",
        "properties": {
            "script": {"type": ["string", "null"]},
            "avatar_description": {"type": ["string", "null"]},
            "creation_log": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
        },
        "additionalProperties": False,
    },
)


__all__ = [
    "CREATION_LOG_FILENAME",
    "CURRENT_AVATAR_DESCRIPTION_FILENAME",
    "CURRENT_SCRIPT_FILENAME",
    "KNOWT_HARNESS_MANIFEST",
    "KnowtAgentConfig",
    "KnowtCreationLogEntry",
    "KnowtMemoryStore",
    "MASTER_PROMPT_FILENAME",
    "PROMPTS_DIRNAME",
]
