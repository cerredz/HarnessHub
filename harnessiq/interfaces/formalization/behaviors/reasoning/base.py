"""
===============================================================================
File: harnessiq/interfaces/formalization/behaviors/reasoning/base.py

What this file does:
- Defines part of the abstract formalization interface surface used to describe
  harness behavior declaratively.
- Typed base classes for reasoning behavior layers.

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

from harnessiq.shared.tools import ToolResult

from ..base import BaseBehaviorLayer, BehaviorConstraint


@dataclass(frozen=True, slots=True)
class ReasoningRequirementSpec:
    """Declare one reasoning requirement."""

    requirement_id: str
    description: str
    before_patterns: tuple[str, ...]
    required_reasoning_patterns: tuple[str, ...]
    reasoning_hint: str = ""


class BaseReasoningBehaviorLayer(BaseBehaviorLayer):
    """Base class for layers that require explicit reasoning steps."""

    @abstractmethod
    def get_reasoning_requirements(self) -> Sequence[ReasoningRequirementSpec]:
        """Return all reasoning requirements declared by the layer."""

    @abstractmethod
    def reasoning_satisfied_for(self, trigger_key: str) -> bool:
        """Return whether the required reasoning is satisfied for one tool."""

    def get_behavioral_constraints(self) -> Sequence[BehaviorConstraint]:
        return tuple(
            BehaviorConstraint(
                constraint_id=requirement.requirement_id,
                description=(
                    requirement.description
                    + (
                        f" Reason about: {requirement.reasoning_hint}"
                        if requirement.reasoning_hint
                        else ""
                    )
                ),
                category="reasoning_behavior",
                enforcement_mode="code_and_prompt",
                enforced_at="filter_tool_keys",
                violation_action="hide_tool",
            )
            for requirement in self.get_reasoning_requirements()
        )

    def filter_tool_keys(self, tool_keys: Sequence[str]) -> tuple[str, ...]:
        permitted: list[str] = []
        for tool_key in tool_keys:
            is_trigger = any(
                _is_tool_allowed(tool_key, requirement.before_patterns)
                for requirement in self.get_reasoning_requirements()
            )
            if is_trigger and not self.reasoning_satisfied_for(tool_key):
                continue
            permitted.append(tool_key)
        return tuple(permitted)

    def on_tool_result(self, result: ToolResult) -> ToolResult:
        for requirement in self.get_reasoning_requirements():
            for pattern in requirement.required_reasoning_patterns:
                if _is_tool_allowed(result.tool_key, (pattern,)):
                    self._on_reasoning_completed(result.tool_key, requirement)
        return result

    def _on_reasoning_completed(
        self,
        tool_key: str,
        requirement: ReasoningRequirementSpec,
    ) -> None:
        del tool_key, requirement


def _is_tool_allowed(tool_key: str, patterns: tuple[str, ...]) -> bool:
    from harnessiq.tools.hooks.defaults import is_tool_allowed

    return is_tool_allowed(tool_key, patterns)
