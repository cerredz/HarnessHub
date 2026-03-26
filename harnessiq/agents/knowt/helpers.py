"""Helper functions for the Knowt agent."""

from __future__ import annotations

from pathlib import Path

from harnessiq.agents.helpers import read_optional_text
from harnessiq.shared.knowt import KnowtMemoryStore


def build_knowt_instance_payload(
    *,
    memory_path: Path,
    max_tokens: int,
    reset_threshold: float,
) -> dict[str, object]:
    """Build the Knowt instance payload from runtime config and memory files."""
    payload: dict[str, object] = {
        "memory_path": str(memory_path),
        "runtime": {
            "max_tokens": max_tokens,
            "reset_threshold": reset_threshold,
        },
    }
    store = KnowtMemoryStore(memory_path=memory_path)
    payload["files"] = {
        "current_avatar_description": read_optional_text(store.current_avatar_description_path),
        "current_script": read_optional_text(store.current_script_path),
    }
    return payload


__all__ = ["build_knowt_instance_payload"]
