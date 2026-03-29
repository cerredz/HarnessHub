"""Typed base classes for error-recovery behavior layers."""

from __future__ import annotations

import json
from abc import abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from harnessiq.shared.agents import AgentPauseSignal
from harnessiq.shared.tools import ToolCall, ToolResult

from ..base import BaseBehaviorLayer, BehaviorConstraint, BehaviorViolationAction


@dataclass(frozen=True, slots=True)
class RecoveryStrategySpec:
    """Declare one monitored recovery strategy."""

    strategy_id: str
    description: str
    applies_to_patterns: tuple[str, ...]
    max_consecutive_errors: int = 3
    on_exceeded: str = "hide_tool"


class BaseErrorRecoveryLayer(BaseBehaviorLayer):
    """Base class for layers that react to failures and repeated attempts."""

    @abstractmethod
    def get_recovery_strategies(self) -> Sequence[RecoveryStrategySpec]:
        """Return the recovery strategies declared by the layer."""

    @abstractmethod
    def handle_tool_call(
        self,
        tool_call: ToolCall,
    ) -> ToolCall | ToolResult | AgentPauseSignal:
        """Inspect one tool call before execution."""

    @abstractmethod
    def handle_tool_result(self, tool_call: ToolCall, result: ToolResult) -> ToolResult:
        """Inspect one tool result with the originating tool-call context."""

    def get_behavioral_constraints(self) -> Sequence[BehaviorConstraint]:
        return tuple(
            BehaviorConstraint(
                constraint_id=strategy.strategy_id,
                description=strategy.description,
                category="error_recovery",
                enforcement_mode="code_and_prompt",
                enforced_at="on_tool_call",
                violation_action=_map_recovery_action(strategy.on_exceeded),
            )
            for strategy in self.get_recovery_strategies()
        )

    def on_tool_call(
        self,
        tool_call: ToolCall,
    ) -> ToolCall | ToolResult | AgentPauseSignal:
        return self.handle_tool_call(tool_call)

    def on_tool_result_event(self, tool_call: ToolCall, result: ToolResult) -> ToolResult:
        return self.handle_tool_result(tool_call, result)


def _map_recovery_action(action: str) -> BehaviorViolationAction:
    return {
        "hide_tool": "block_result",
        "pause": "pause",
        "switch_strategy": "warn",
    }.get(action, "block_result")


def _is_tool_allowed(tool_key: str, patterns: tuple[str, ...]) -> bool:
    from harnessiq.tools.hooks.defaults import is_tool_allowed

    return is_tool_allowed(tool_key, patterns)


def _is_error_result(result: ToolResult) -> bool:
    return isinstance(result.output, dict) and "error" in result.output


def _fingerprint_arguments(arguments: Mapping[str, Any]) -> str:
    return json.dumps(dict(arguments), sort_keys=True, separators=(",", ":"), default=str)


__all__ = [
    "BaseErrorRecoveryLayer",
    "RecoveryStrategySpec",
]
