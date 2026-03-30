"""
===============================================================================
File: harnessiq/interfaces/formalization/behaviors/pace/base.py

What this file does:
- Defines part of the abstract formalization interface surface used to describe
  harness behavior declaratively.
- Typed base classes for execution-pace behavior layers.

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
class PaceRuleSpec:
    """Declare one cadence or pacing rule."""

    rule_id: str
    description: str
    trigger_every_n: int
    trigger_unit: str
    required_action_patterns: tuple[str, ...]
    blocked_until_satisfied: tuple[str, ...] = ()


class BaseExecutionPaceLayer(BaseBehaviorLayer):
    """Base class for layers that govern execution cadence."""

    @abstractmethod
    def get_pace_rules(self) -> Sequence[PaceRuleSpec]:
        """Return all execution-pace rules declared by the layer."""

    @abstractmethod
    def is_pace_rule_satisfied(self, rule: PaceRuleSpec) -> bool:
        """Return whether the rule is currently satisfied."""

    @abstractmethod
    def record_pace_action(self, tool_key: str, rule: PaceRuleSpec) -> None:
        """Record a tool call that satisfies the rule."""

    def get_behavioral_constraints(self) -> Sequence[BehaviorConstraint]:
        return tuple(
            BehaviorConstraint(
                constraint_id=rule.rule_id,
                description=rule.description,
                category="execution_pace",
                enforcement_mode="code_and_prompt",
                enforced_at="filter_tool_keys",
                violation_action="hide_tool",
            )
            for rule in self.get_pace_rules()
        )

    def filter_tool_keys(self, tool_keys: Sequence[str]) -> tuple[str, ...]:
        permitted = set(tool_keys)
        for rule in self.get_pace_rules():
            if self.is_pace_rule_satisfied(rule):
                continue
            for tool_key in tool_keys:
                if any(
                    _is_tool_allowed(tool_key, (pattern,))
                    for pattern in rule.required_action_patterns
                ):
                    continue
                if any(
                    _is_tool_allowed(tool_key, (pattern,))
                    for pattern in rule.blocked_until_satisfied
                ):
                    permitted.discard(tool_key)
        return tuple(tool_key for tool_key in tool_keys if tool_key in permitted)

    def on_tool_result(self, result: ToolResult) -> ToolResult:
        for rule in self.get_pace_rules():
            if any(
                _is_tool_allowed(result.tool_key, (pattern,))
                for pattern in rule.required_action_patterns
            ):
                self.record_pace_action(result.tool_key, rule)
        return result


def _is_tool_allowed(tool_key: str, patterns: tuple[str, ...]) -> bool:
    from harnessiq.tools.hooks.defaults import is_tool_allowed

    return is_tool_allowed(tool_key, patterns)
