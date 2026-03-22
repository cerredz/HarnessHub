"""Shared helper functions for JSON-oriented CLI command modules."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any


def add_agent_options(
    parser: argparse.ArgumentParser,
    *,
    agent_help: str,
    memory_root_default: str,
    memory_root_help: str,
) -> None:
    """Register the common ``--agent`` and ``--memory-root`` options."""
    parser.add_argument("--agent", required=True, help=agent_help)
    parser.add_argument(
        "--memory-root",
        default=memory_root_default,
        help=memory_root_help,
    )


def add_text_or_file_options(
    parser: argparse.ArgumentParser,
    field_name: str,
    label: str,
) -> None:
    """Register a mutually-exclusive ``--<field>-text`` / ``--<field>-file`` pair."""
    group = parser.add_mutually_exclusive_group()
    option_name = field_name.replace("_", "-")
    group.add_argument(f"--{option_name}-text", help=f"{label} content provided inline.")
    group.add_argument(
        f"--{option_name}-file",
        help=f"Path to a UTF-8 text file containing {label.lower()} content.",
    )


def resolve_memory_path(
    agent_name: str,
    memory_root: str,
    *,
    slugifier: Callable[[str], str] | None = None,
) -> Path:
    """Resolve the memory directory for a logical agent name."""
    normalize_name = slugifier or slugify_agent_name
    return Path(memory_root).expanduser() / normalize_name(agent_name)


def slugify_agent_name(agent_name: str) -> str:
    """Normalize a logical agent name into a filesystem-friendly directory name."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", agent_name.strip()).strip("-")
    if not cleaned:
        raise ValueError("Agent names must contain at least one alphanumeric character.")
    return cleaned


def resolve_text_argument(text_value: str | None, file_value: str | None) -> str | None:
    """Resolve a CLI value passed inline or from a UTF-8 text file."""
    if text_value is not None:
        return text_value
    if file_value is not None:
        return Path(file_value).read_text(encoding="utf-8")
    return None


def parse_generic_assignments(assignments: Sequence[str]) -> dict[str, Any]:
    """Parse ``KEY=VALUE`` pairs, decoding JSON scalars when possible."""
    parsed: dict[str, Any] = {}
    for assignment in assignments:
        key, raw_value = split_assignment(assignment)
        parsed[key] = parse_scalar(raw_value)
    return parsed


def split_assignment(assignment: str) -> tuple[str, str]:
    """Split a required ``KEY=VALUE`` assignment."""
    key, separator, value = assignment.partition("=")
    if not separator:
        raise ValueError(f"Expected KEY=VALUE assignment, received '{assignment}'.")
    normalized_key = key.strip()
    if not normalized_key:
        raise ValueError(f"Expected a non-empty key in assignment '{assignment}'.")
    return normalized_key, value


def parse_scalar(value: str) -> Any:
    """Parse a JSON-like scalar string, falling back to the original text."""
    trimmed = value.strip()
    if not trimmed:
        return ""
    try:
        return json.loads(trimmed)
    except json.JSONDecodeError:
        return value


def emit_json(payload: dict[str, Any]) -> None:
    """Render deterministic JSON for CLI command results."""
    print(json.dumps(payload, indent=2, sort_keys=True, default=_json_default))


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return os.fspath(value)
    return str(value)


__all__ = [
    "add_agent_options",
    "add_text_or_file_options",
    "emit_json",
    "parse_generic_assignments",
    "parse_scalar",
    "resolve_memory_path",
    "resolve_text_argument",
    "slugify_agent_name",
    "split_assignment",
]
