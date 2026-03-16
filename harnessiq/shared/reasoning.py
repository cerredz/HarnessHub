"""Shared behavioral constants for the core injectable reasoning tools.

These constants govern the valid parameter ranges for ``reason.brainstorm`` and
``reason.chain_of_thought``.  Keeping them in the shared package makes them
importable by any module that needs to reference the same bounds — for example,
documentation generators, CLI help text, or future reasoning tool variants —
without importing the full tool implementation.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Brainstorm bounds
# ---------------------------------------------------------------------------

BRAINSTORM_COUNT_MIN: int = 5
BRAINSTORM_COUNT_MAX: int = 30
BRAINSTORM_COUNT_DEFAULT: int = 10

# Human-readable presets that resolve to concrete idea counts.
BRAINSTORM_COUNT_PRESETS: dict[str, int] = {
    "small": 5,
    "medium": 15,
    "large": 30,
}

# ---------------------------------------------------------------------------
# Chain-of-thought bounds
# ---------------------------------------------------------------------------

COT_STEPS_MIN: int = 3
COT_STEPS_MAX: int = 10
COT_STEPS_DEFAULT: int = 5

__all__ = [
    "BRAINSTORM_COUNT_DEFAULT",
    "BRAINSTORM_COUNT_MAX",
    "BRAINSTORM_COUNT_MIN",
    "BRAINSTORM_COUNT_PRESETS",
    "COT_STEPS_DEFAULT",
    "COT_STEPS_MAX",
    "COT_STEPS_MIN",
]
