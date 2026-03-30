"""
===============================================================================
File: harnessiq/agents/knowt/helpers.py

What this file does:
- Collects shared helper functions for the `knowt` package.
- Helper functions for the Knowt agent.

Use cases:
- Use these helpers when sibling runtime modules need the same normalization,
  path resolution, or payload-shaping logic.

How to use it:
- Import the narrow helper you need from `harnessiq/agents/knowt` rather than
  duplicating package-specific support code.

Intent:
- Keep reusable `knowt` support logic centralized so business modules stay
  focused on orchestration.
===============================================================================
"""

from __future__ import annotations

from pathlib import Path

from harnessiq.agents.helpers import read_optional_text
from harnessiq.shared.dtos import KnowtAgentInstancePayload
from harnessiq.shared.knowt import KnowtMemoryStore


def build_knowt_instance_payload(
    *,
    memory_path: Path,
    max_tokens: int,
    reset_threshold: float,
) -> KnowtAgentInstancePayload:
    """Build the Knowt instance payload from runtime config and memory files."""
    store = KnowtMemoryStore(memory_path=memory_path)
    return KnowtAgentInstancePayload(
        memory_path=memory_path,
        runtime={
            "max_tokens": max_tokens,
            "reset_threshold": reset_threshold,
        },
        files={
            "current_avatar_description": read_optional_text(store.current_avatar_description_path),
            "current_script": read_optional_text(store.current_script_path),
        },
    )


__all__ = ["build_knowt_instance_payload"]
