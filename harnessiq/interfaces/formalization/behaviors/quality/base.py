"""
===============================================================================
File: harnessiq/interfaces/formalization/behaviors/quality/base.py

What this file does:
- Defines part of the abstract formalization interface surface used to describe
  harness behavior declaratively.
- Typed base classes for quality behavior layers.

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

from abc import abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from harnessiq.shared.tools import CONTROL_MARK_COMPLETE, ToolResult

from ..base import BaseBehaviorLayer, BehaviorConstraint


@dataclass(frozen=True, slots=True)
class QualityCriterionSpec:
    """Declare one quality criterion."""

    criterion_id: str
    description: str
    gating: bool = True


class BaseQualityBehaviorLayer(BaseBehaviorLayer):
    """Base class for layers that gate work on quality and scope."""

    @abstractmethod
    def get_quality_criteria(self) -> Sequence[QualityCriterionSpec]:
        """Return all quality criteria declared by the layer."""

    @abstractmethod
    def evaluate_criterion(
        self,
        criterion: QualityCriterionSpec,
        agent_state: dict[str, Any],
    ) -> tuple[bool, str]:
        """Return whether one criterion passes along with a failure reason."""

    def get_behavioral_constraints(self) -> Sequence[BehaviorConstraint]:
        return tuple(
            BehaviorConstraint(
                constraint_id=criterion.criterion_id,
                description=criterion.description,
                category="quality_behavior",
                enforcement_mode="code_and_prompt",
                enforced_at="on_tool_result",
                violation_action="block_result",
            )
            for criterion in self.get_quality_criteria()
            if criterion.gating
        )

    def on_tool_result(self, result: ToolResult) -> ToolResult:
        if result.tool_key != CONTROL_MARK_COMPLETE:
            return result
        failures: list[str] = []
        agent_state = self._build_agent_state()
        for criterion in self.get_quality_criteria():
            if not criterion.gating:
                continue
            passes, reason = self.evaluate_criterion(criterion, agent_state)
            if not passes:
                failures.append(f"[{criterion.criterion_id}] {reason}")
        if not failures:
            return result
        return ToolResult(
            tool_key=result.tool_key,
            output={
                "error": "Completion blocked. Quality criteria not met:\n" + "\n".join(failures),
                "failed_criteria": [
                    failure.split("]")[0].strip("[")
                    for failure in failures
                ],
            },
        )

    def _build_agent_state(self) -> dict[str, Any]:
        return {}
