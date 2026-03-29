from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from harnessiq.formalization.base import LayerRuleRecord
from harnessiq.shared.tools import RegisteredTool

from .context import StageContext


class StageSpec(ABC):
    """Abstract base class for one execution stage inside a staged runtime."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique identifier for this stage."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Return the one-sentence description of this stage's goal."""

    @abstractmethod
    def build_system_prompt_fragment(self) -> str:
        """Return stage-specific system prompt text."""

    @abstractmethod
    def build_tools(self, memory_path: Path) -> Sequence[RegisteredTool]:
        """Return the tools active during this stage."""

    @abstractmethod
    def is_complete(self, outputs: dict[str, Any]) -> bool:
        """Return whether the supplied outputs satisfy this stage."""

    @property
    def allowed_tool_patterns(self) -> tuple[str, ...]:
        """Return the base-executor tool patterns allowed during this stage."""
        return ()

    @property
    def required_output_keys(self) -> tuple[str, ...]:
        """Return output keys required before this stage can complete."""
        return ()

    def get_next_stage(self, outputs: dict[str, Any]) -> str | None:
        """Return a non-linear destination stage name or ``None`` for linear flow."""
        del outputs
        return None

    def on_enter(self, context: StageContext) -> None:
        """Run deterministic work when this stage becomes active."""
        del context

    def on_exit(
        self,
        outputs: dict[str, Any],
        context: StageContext,
    ) -> None:
        """Run deterministic work when this stage completes."""
        del outputs, context

    def get_completion_hint(self) -> str:
        """Return a natural-language description of stage completion."""
        return ""

    def get_next_stage_hint(self) -> str:
        """Return a natural-language preview of the following stage."""
        return ""

    @property
    def persist_outputs(self) -> bool:
        """Return whether stage outputs should be durably persisted on advancement."""
        return True

    def _describe_identity(self) -> str:
        """Return the default self-description for this stage."""
        return (
            f"Stage '{self.name}': {self.description} "
            "This stage has its own tool set and system prompt fragment that "
            "are active only while this stage is running."
        )

    def _describe_contract(self) -> str:
        lines: list[str] = [
            f"Call formalization.stage_complete when: {self.get_completion_hint() or 'the stage goal is met'}.",
        ]
        if self.required_output_keys:
            keys = ", ".join(self.required_output_keys)
            lines.append(
                f"stage_complete must include outputs for: {keys}. Missing keys block advancement."
            )
        if self.allowed_tool_patterns:
            patterns = ", ".join(self.allowed_tool_patterns)
            lines.append(f"Base executor tools are filtered to patterns: {patterns}.")
        return "\n".join(lines)

    def _describe_rules(self) -> tuple[LayerRuleRecord, ...]:
        rules: list[LayerRuleRecord] = []
        if self.required_output_keys:
            rules.append(
                LayerRuleRecord(
                    rule_id=f"STAGE-{self.name.upper()}-REQUIRED-OUTPUTS",
                    description=(
                        f"stage_complete for '{self.name}' is blocked unless "
                        f"outputs= contains [{', '.join(self.required_output_keys)}]."
                    ),
                    enforced_at="on_tool_result",
                    enforcement_type="transform",
                )
            )
        if self.allowed_tool_patterns:
            rules.append(
                LayerRuleRecord(
                    rule_id=f"STAGE-{self.name.upper()}-TOOL-FILTER",
                    description=(
                        f"Base executor tools not matching [{', '.join(self.allowed_tool_patterns)}] "
                        f"are hidden while this stage is active."
                    ),
                    enforced_at="filter_tool_keys",
                    enforcement_type="block",
                )
            )
        return tuple(rules)

    def _describe_configuration(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "required_output_keys": list(self.required_output_keys),
            "allowed_tool_patterns": list(self.allowed_tool_patterns),
            "completion_hint": self.get_completion_hint(),
            "persist_outputs": self.persist_outputs,
        }
