"""Typed base classes for tool-calling behavior layers."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from harnessiq.shared.tools import ToolResult

from ..base import BaseBehaviorLayer, BehaviorConstraint


@dataclass(frozen=True, slots=True)
class ToolConstraintSpec:
    """Declare one deterministic constraint on tool-calling behavior."""

    constraint_id: str
    tool_patterns: tuple[str, ...]
    description: str
    limit: int | None = None
    cooldown_tools: tuple[str, ...] = ()
    prerequisite_patterns: tuple[str, ...] = ()


class BaseToolBehaviorLayer(BaseBehaviorLayer):
    """Base class for layers that constrain how tools are called."""

    @abstractmethod
    def get_tool_constraints(self) -> Sequence[ToolConstraintSpec]:
        """Return all tool-call constraints declared by the layer."""

    @abstractmethod
    def is_tool_call_permitted(
        self,
        tool_key: str,
        reset_count: int,
        cycle_index: int,
    ) -> tuple[bool, str]:
        """Return whether one visible tool key should remain callable."""

    @abstractmethod
    def record_tool_call(self, tool_key: str) -> None:
        """Record one completed tool call."""

    def get_behavioral_constraints(self) -> Sequence[BehaviorConstraint]:
        return tuple(
            BehaviorConstraint(
                constraint_id=spec.constraint_id,
                description=spec.description,
                category="tool_behavior",
                enforcement_mode="code_and_prompt",
                enforced_at="filter_tool_keys",
                violation_action="hide_tool",
            )
            for spec in self.get_tool_constraints()
        )

    def filter_tool_keys(self, tool_keys: Sequence[str]) -> tuple[str, ...]:
        permitted: list[str] = []
        for tool_key in tool_keys:
            allowed, _reason = self.is_tool_call_permitted(
                tool_key,
                getattr(self, "_reset_count", 0),
                getattr(self, "_cycle_index", 0),
            )
            if allowed:
                permitted.append(tool_key)
        return tuple(permitted)

    def on_tool_result(self, result: ToolResult) -> ToolResult:
        self.record_tool_call(result.tool_key)
        self._cycle_index = getattr(self, "_cycle_index", 0) + 1
        return result

    def on_agent_prepare(self, *, agent_name: str, memory_path: str) -> None:
        del agent_name, memory_path
        self._reset_count = 0
        self._cycle_index = 0

    def on_post_reset(self) -> None:
        self._reset_count = getattr(self, "_reset_count", 0) + 1
