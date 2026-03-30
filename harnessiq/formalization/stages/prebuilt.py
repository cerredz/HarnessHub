"""
===============================================================================
File: harnessiq/formalization/stages/prebuilt.py

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

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from harnessiq.shared.tools import RegisteredTool

from .spec import StageSpec


class SimpleStageSpec(StageSpec):
    """Convenience ``StageSpec`` for stages that need no custom Python logic."""

    def __init__(
        self,
        *,
        name: str,
        description: str,
        system_prompt_fragment: str = "",
        tools: Sequence[RegisteredTool] = (),
        allowed_tool_patterns: tuple[str, ...] = (),
        required_output_keys: tuple[str, ...] = (),
        completion_hint: str = "",
        next_stage_hint: str = "",
        next_stage: str | None = None,
        persist_outputs: bool = True,
    ) -> None:
        self._name = name
        self._description = description
        self._fragment = system_prompt_fragment
        self._tools = tuple(tools)
        self._allowed_patterns = allowed_tool_patterns
        self._required_keys = required_output_keys
        self._completion_hint = completion_hint
        self._next_stage_hint = next_stage_hint
        self._next_stage = next_stage
        self._persist = persist_outputs

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def build_system_prompt_fragment(self) -> str:
        return self._fragment

    def build_tools(self, memory_path: Path) -> Sequence[RegisteredTool]:
        del memory_path
        return self._tools

    def is_complete(self, outputs: dict[str, Any]) -> bool:
        del outputs
        return True

    @property
    def allowed_tool_patterns(self) -> tuple[str, ...]:
        return self._allowed_patterns

    @property
    def required_output_keys(self) -> tuple[str, ...]:
        return self._required_keys

    def get_next_stage(self, outputs: dict[str, Any]) -> str | None:
        del outputs
        return self._next_stage

    def get_completion_hint(self) -> str:
        return self._completion_hint

    def get_next_stage_hint(self) -> str:
        return self._next_stage_hint

    @property
    def persist_outputs(self) -> bool:
        return self._persist
