"""Typed base classes for communication behavior layers."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from harnessiq.shared.tools import ToolResult

from ..base import BaseBehaviorLayer, BehaviorConstraint


@dataclass(frozen=True, slots=True)
class CommunicationRuleSpec:
    """Declare one communication requirement."""

    rule_id: str
    description: str
    required_tool_patterns: tuple[str, ...]
    trigger: str
    trigger_n: int = 1
    blocks_patterns: tuple[str, ...] = ()


class BaseCommunicationBehaviorLayer(BaseBehaviorLayer):
    """Base class for layers that require explicit communication steps."""

    @abstractmethod
    def get_communication_rules(self) -> Sequence[CommunicationRuleSpec]:
        """Return the communication rules declared by the layer."""

    @abstractmethod
    def is_communication_due(self, rule: CommunicationRuleSpec) -> bool:
        """Return whether one communication rule is currently due."""

    @abstractmethod
    def record_communication(self, tool_key: str, rule: CommunicationRuleSpec) -> None:
        """Record that a communication action satisfied one rule."""

    def get_behavioral_constraints(self) -> Sequence[BehaviorConstraint]:
        return tuple(
            BehaviorConstraint(
                constraint_id=rule.rule_id,
                description=rule.description,
                category="communication_behavior",
                enforcement_mode="code_and_prompt",
                enforced_at="filter_tool_keys",
                violation_action="hide_tool",
            )
            for rule in self.get_communication_rules()
        )

    def filter_tool_keys(self, tool_keys: Sequence[str]) -> tuple[str, ...]:
        pending_blocks: set[str] = set()
        for rule in self.get_communication_rules():
            if not self.is_communication_due(rule):
                continue
            for tool_key in tool_keys:
                if any(_is_tool_allowed(tool_key, (pattern,)) for pattern in rule.blocks_patterns):
                    pending_blocks.add(tool_key)
        return tuple(tool_key for tool_key in tool_keys if tool_key not in pending_blocks)

    def on_tool_result(self, result: ToolResult) -> ToolResult:
        for rule in self.get_communication_rules():
            if any(
                _is_tool_allowed(result.tool_key, (pattern,))
                for pattern in rule.required_tool_patterns
            ):
                self.record_communication(result.tool_key, rule)
        return result


def _is_tool_allowed(tool_key: str, patterns: tuple[str, ...]) -> bool:
    from harnessiq.tools.hooks.defaults import is_tool_allowed

    return is_tool_allowed(tool_key, patterns)


__all__ = [
    "BaseCommunicationBehaviorLayer",
    "CommunicationRuleSpec",
]
