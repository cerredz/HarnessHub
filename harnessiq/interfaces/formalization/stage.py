"""
===============================================================================
File: harnessiq/interfaces/formalization/stage.py

What this file does:
- Defines part of the abstract formalization interface surface used to describe
  harness behavior declaratively.
- Abstract staged-execution layer for deterministic multi-phase harnesses.
  Stage layers describe ordered execution phases. They are responsible for
  projecting stage-specific prompt fragments, narrowing visible tools, and
  declaring the outputs that make a stage complete. The runtime can later wire
  those declarations into reset-driven advancement or other deterministic flow.

Use cases:
- Subclass or import these interfaces when building a new formalization layer
  family or behavior.

How to use it:
- Use the abstractions here to declare behavior, rules, and configuration in a
  form the runtime can later inspect or enforce.

Intent:
- Keep formalization contracts explicit and composable so harness rules are
  visible in code and docs.
===============================================================================
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from typing import Any

from harnessiq.shared.agents import AgentParameterSection, json_parameter_section
from harnessiq.shared.formalization import LayerRuleRecord, StageSpec

from .base import BaseFormalizationLayer


class BaseStageLayer(BaseFormalizationLayer, ABC):
    """Typed base for deterministic staged execution layers."""

    @abstractmethod
    def get_stages(self) -> Sequence[StageSpec]:
        """Return the ordered stage specification for this layer."""

    @abstractmethod
    def get_current_stage_index(self) -> int:
        """Return the zero-based active stage index."""

    @property
    def current_stage(self) -> StageSpec:
        """Return the currently active stage."""
        stages = tuple(self.get_stages())
        return stages[self.get_current_stage_index()]

    def augment_system_prompt(self, system_prompt: str) -> str:
        fragment = self.current_stage.system_prompt_fragment.strip()
        if not fragment:
            return system_prompt
        return f"{system_prompt}\n\n{fragment}"

    def filter_tool_keys(self, tool_keys: Sequence[str]) -> tuple[str, ...]:
        return self._filter_with_patterns(tool_keys, self.current_stage.allowed_tool_patterns)

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        current_stage = self.current_stage
        stage_payload = {
            "stage_index": self.get_current_stage_index(),
            "stage_name": current_stage.name,
            "description": current_stage.description,
            "required_output_keys": list(current_stage.required_output_keys),
            "completion_hint": current_stage.completion_hint,
            "allowed_tool_patterns": list(current_stage.allowed_tool_patterns),
        }
        return (
            *super().get_parameter_sections(),
            json_parameter_section("Current Stage", stage_payload),
        )

    def _describe_identity(self) -> str:
        stages = tuple(self.get_stages())
        names = [stage.name for stage in stages]
        return self._compose_identity(
            what=(
                "This layer formalizes a staged harness where execution proceeds through an "
                "ordered list of named phases."
            ),
            why=(
                "Staged work benefits from deterministic sequencing so each context window knows "
                "which objectives, tools, and completion conditions currently apply."
            ),
            how=(
                f"Declared stages: {' -> '.join(names) or 'none'}. "
                f"Active stage index: {self.get_current_stage_index()}."
            ),
            intent=(
                "Keep phase progression, prompt context, and tool visibility aligned through one "
                "self-documenting interface."
            ),
        )

    def _describe_contract(self) -> str:
        stage_lines = []
        for index, stage in enumerate(self.get_stages(), start=1):
            hint = "" if stage.completion_hint is None else f" Done when: {stage.completion_hint}."
            required = (
                ""
                if not stage.required_output_keys
                else f" Required outputs: {', '.join(stage.required_output_keys)}."
            )
            tools = (
                ""
                if not stage.allowed_tool_patterns
                else f" Allowed tool patterns: {', '.join(stage.allowed_tool_patterns)}."
            )
            stage_lines.append(
                f"- {index}. {stage.name}: {self._ensure_sentence(stage.description)}{required}{tools}{hint}"
            )
        return (
            "This layer defines the ordered execution phases for the harness.\n\n"
            "Stages:\n"
            + ("\n".join(stage_lines) or "- No stages declared.")
        )

    def _describe_rules(self) -> Sequence[LayerRuleRecord]:
        rules: list[LayerRuleRecord] = [
            LayerRuleRecord(
                rule_id="STAGE-TOOL-FILTER",
                description="The active stage narrows the visible tool surface to its allowed tool patterns.",
                enforced_at="filter_tool_keys",
                enforcement_type="block",
            )
        ]
        for index, stage in enumerate(self.get_stages(), start=1):
            if not stage.required_output_keys:
                continue
            rules.append(
                LayerRuleRecord(
                    rule_id=f"STAGE-{index}-OUTPUTS",
                    description=(
                        f"Stage `{stage.name}` should not be considered complete until it has produced: "
                        + ", ".join(stage.required_output_keys)
                        + "."
                    ),
                    enforced_at="on_tool_result",
                    enforcement_type="transform",
                )
            )
        return tuple(rules)

    def _describe_configuration(self) -> Mapping[str, Any]:
        return {
            "current_stage_index": self.get_current_stage_index(),
            "stages": [asdict(stage) for stage in self.get_stages()],
        }


__all__ = ["BaseStageLayer"]
