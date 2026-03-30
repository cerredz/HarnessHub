"""
===============================================================================
File: harnessiq/agents/research_sweep/helpers.py

What this file does:
- Collects shared helper functions for the `research_sweep` package.
- Helper functions for the Research Sweep agent.

Use cases:
- Use these helpers when sibling runtime modules need the same normalization,
  path resolution, or payload-shaping logic.

How to use it:
- Import the narrow helper you need from `harnessiq/agents/research_sweep`
  rather than duplicating package-specific support code.

Intent:
- Keep reusable `research_sweep` support logic centralized so business modules
  stay focused on orchestration.
===============================================================================
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from harnessiq.tools.context import rebuild_context_window, split_context_window


def append_transcript_entry(agent: Any, entry: dict[str, Any]) -> list[dict[str, Any]]:
    """Append a transcript entry onto an agent's current context window."""
    parameter_entries, transcript_entries = split_context_window(agent.build_context_window())
    copied_transcript = [deepcopy(item) for item in transcript_entries]
    copied_transcript.append(entry)
    return rebuild_context_window(parameter_entries, copied_transcript)


def utc_today() -> str:
    """Return the current UTC date in ISO-8601 format."""
    return datetime.now(timezone.utc).date().isoformat()


__all__ = ["append_transcript_entry", "utc_today"]
