"""
===============================================================================
File: harnessiq/formalization/artifacts/format_map.py

What this file does:
- Implements part of the runtime formalization layer that turns declarative
  contracts into executable HarnessIQ behavior.

Use cases:
- Use this module when wiring staged execution, artifacts, or reusable
  formalization runtime helpers into an agent.

How to use it:
- Import the runtime classes or helpers from this module through the
  formalization package and compose them into the agent runtime.

Intent:
- Make formalization rules operational in Python so important workflow
  constraints are enforced deterministically.
===============================================================================
"""

from __future__ import annotations

from pathlib import Path

from harnessiq.shared.tools import (
    ARTIFACT_APPEND_RUN_LOG,
    ARTIFACT_WRITE_CSV,
    ARTIFACT_WRITE_JSON,
    ARTIFACT_WRITE_MARKDOWN,
    FILESYSTEM_REPLACE_TEXT_FILE,
)

from .output_spec import OutputArtifactSpec

FORMAT_TOOL_MAP: dict[str, str] = {
    "markdown": ARTIFACT_WRITE_MARKDOWN,
    "json": ARTIFACT_WRITE_JSON,
    "csv": ARTIFACT_WRITE_CSV,
    "jsonl": ARTIFACT_APPEND_RUN_LOG,
    "text": FILESYSTEM_REPLACE_TEXT_FILE,
}

FORMAT_EXTENSION_MAP: dict[str, str] = {
    "markdown": ".md",
    "json": ".json",
    "csv": ".csv",
    "jsonl": ".jsonl",
    "text": ".txt",
}


def resolve_artifact_path(
    raw_path: str | Path,
    *,
    memory_path: Path,
    name: str,
) -> Path:
    """Resolve a templated artifact path against the active memory root."""
    template = str(raw_path)
    rendered = template.replace("{memory_path}", str(memory_path))
    rendered = rendered.replace("{name}", name)
    candidate = Path(rendered)
    if "{memory_path}" in template or candidate.is_absolute():
        return candidate
    return memory_path / candidate


def resolve_write_tool_key(spec: OutputArtifactSpec) -> str:
    """Resolve the write tool key for one output artifact spec."""
    if spec.write_tool_key is not None:
        return spec.write_tool_key
    return FORMAT_TOOL_MAP[spec.file_format]


def resolve_output_path(spec: OutputArtifactSpec, memory_path: Path) -> Path:
    """Resolve the concrete output path for one output artifact spec."""
    if spec.path is not None:
        return resolve_artifact_path(spec.path, memory_path=memory_path, name=spec.name)

    extension = FORMAT_EXTENSION_MAP[spec.file_format]
    if spec.file_format == "text":
        return memory_path / "outputs" / f"{spec.name}{extension}"
    return memory_path / "artifacts" / f"{spec.name}{extension}"


__all__ = [
    "FORMAT_EXTENSION_MAP",
    "FORMAT_TOOL_MAP",
    "resolve_artifact_path",
    "resolve_output_path",
    "resolve_write_tool_key",
]
