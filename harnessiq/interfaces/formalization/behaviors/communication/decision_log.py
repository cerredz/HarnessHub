"""Concrete decision-logging behavior."""

from __future__ import annotations

from harnessiq.shared.agents import AgentParameterSection
from harnessiq.shared.tools import CONTROL_EMIT_DECISION, ToolResult

from .base import BaseCommunicationBehaviorLayer, CommunicationRuleSpec, _is_tool_allowed


class DecisionLoggingBehavior(BaseCommunicationBehaviorLayer):
    """Require explicit decision logging before sensitive actions."""

    def __init__(
        self,
        *,
        target_patterns: tuple[str, ...],
        decision_patterns: tuple[str, ...] = (CONTROL_EMIT_DECISION,),
    ) -> None:
        if not target_patterns:
            raise ValueError("target_patterns must not be empty.")
        if not decision_patterns:
            raise ValueError("decision_patterns must not be empty.")
        self._target_patterns = tuple(target_patterns)
        self._decision_patterns = tuple(decision_patterns)
        self._decision_ready = False
        self._last_decision_tool: str | None = None

    def get_communication_rules(self) -> tuple[CommunicationRuleSpec, ...]:
        return (
            CommunicationRuleSpec(
                rule_id="DECISION_LOGGING_REQUIRED",
                description=(
                    f"Before tools matching {self._target_patterns} are used, "
                    f"log a decision with tools matching {self._decision_patterns}."
                ),
                required_tool_patterns=self._decision_patterns,
                trigger="before_target_action",
                trigger_n=1,
                blocks_patterns=self._target_patterns,
            ),
        )

    def is_communication_due(self, rule: CommunicationRuleSpec) -> bool:
        del rule
        return not self._decision_ready

    def record_communication(self, tool_key: str, rule: CommunicationRuleSpec) -> None:
        del rule
        self._decision_ready = True
        self._last_decision_tool = tool_key

    def on_tool_result(self, result: ToolResult) -> ToolResult:
        if _is_tool_allowed(result.tool_key, self._target_patterns):
            self._decision_ready = False
        return super().on_tool_result(result)

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        lines = [
            f"Decision ready: {'yes' if self._decision_ready else 'no'}",
            f"Target patterns: {self._target_patterns}",
            f"Decision patterns: {self._decision_patterns}",
            f"Last decision tool: {self._last_decision_tool or 'none'}",
        ]
        return (
            *super().get_parameter_sections(),
            AgentParameterSection(title=f"Behavior State: {self.layer_id}", content="\n".join(lines)),
        )


__all__ = ["DecisionLoggingBehavior"]
