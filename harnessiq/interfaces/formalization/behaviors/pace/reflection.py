"""Concrete reflection-cadence behavior."""

from __future__ import annotations

from harnessiq.shared.agents import AgentParameterSection
from harnessiq.shared.tools import ToolResult
from harnessiq.tools.hooks.defaults import is_tool_allowed

from .base import BaseExecutionPaceLayer, PaceRuleSpec


class ReflectionCadenceBehavior(BaseExecutionPaceLayer):
    """Require periodic reasoning calls between non-reasoning action bursts."""

    def __init__(
        self,
        every_n_calls: int = 5,
        reasoning_patterns: tuple[str, ...] = ("reason.*", "reasoning.*"),
        blocked_until_reflected: tuple[str, ...] = ("*",),
    ) -> None:
        self._every_n_calls = int(every_n_calls)
        self._reasoning_patterns = tuple(reasoning_patterns)
        self._blocked_patterns = tuple(blocked_until_reflected)
        self._calls_since_reflection = 0
        self._reflection_pending = False

    def get_pace_rules(self) -> tuple[PaceRuleSpec, ...]:
        return (
            PaceRuleSpec(
                rule_id="REFLECT_EVERY_N",
                description=(
                    f"After every {self._every_n_calls} non-reasoning tool calls, a tool "
                    f"matching {self._reasoning_patterns} must be called before blocked "
                    "action tools become visible again."
                ),
                trigger_every_n=self._every_n_calls,
                trigger_unit="tool_calls",
                required_action_patterns=self._reasoning_patterns,
                blocked_until_satisfied=self._blocked_patterns,
            ),
        )

    def is_pace_rule_satisfied(self, rule: PaceRuleSpec) -> bool:
        del rule
        return not self._reflection_pending

    def record_pace_action(self, tool_key: str, rule: PaceRuleSpec) -> None:
        del tool_key, rule
        self._reflection_pending = False
        self._calls_since_reflection = 0

    def on_tool_result(self, result: ToolResult) -> ToolResult:
        if any(is_tool_allowed(result.tool_key, (pattern,)) for pattern in self._reasoning_patterns):
            self._reflection_pending = False
            self._calls_since_reflection = 0
            return super().on_tool_result(result)
        self._calls_since_reflection += 1
        if self._calls_since_reflection >= self._every_n_calls:
            self._reflection_pending = True
        return super().on_tool_result(result)

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        status = "pending" if self._reflection_pending else "satisfied"
        content = "\n".join(
            [
                f"Reflection status: {status}",
                f"Calls since reflection: {self._calls_since_reflection}/{self._every_n_calls}",
                f"Reasoning patterns: {self._reasoning_patterns}",
            ]
        )
        return (
            *super().get_parameter_sections(),
            AgentParameterSection(title=f"Behavior State: {self.layer_id}", content=content),
        )
