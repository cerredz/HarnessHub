"""
===============================================================================
File: harnessiq/formalization/stages/context.py

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

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class StageContext:
    """Runtime context passed to every stage lifecycle hook."""

    agent_name: str
    memory_path: Path
    reset_count: int
    stage_index: int
    stage_name: str
    prior_stage_outputs: dict[str, dict[str, Any]]
    metadata: dict[str, Any]
