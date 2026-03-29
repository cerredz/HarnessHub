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
