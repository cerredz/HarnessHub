"""Concrete error-escalation behavior."""

from __future__ import annotations

from harnessiq.shared.agents import AgentParameterSection, AgentPauseSignal
from harnessiq.shared.tools import ToolCall, ToolResult

from .base import BaseErrorRecoveryLayer, RecoveryStrategySpec, _is_error_result, _is_tool_allowed


class ErrorEscalationBehavior(BaseErrorRecoveryLayer):
    """Pause the run after too many consecutive failures."""

    def __init__(
        self,
        *,
        monitored_patterns: tuple[str, ...] = ("*",),
        max_consecutive_failures: int = 3,
    ) -> None:
        if max_consecutive_failures <= 0:
            raise ValueError("max_consecutive_failures must be greater than zero.")
        self._monitored_patterns = tuple(monitored_patterns)
        self._max_consecutive_failures = max_consecutive_failures
        self._consecutive_failures = 0
        self._recent_failures: list[dict[str, object]] = []

    def get_recovery_strategies(self) -> tuple[RecoveryStrategySpec, ...]:
        return (
            RecoveryStrategySpec(
                strategy_id="ERROR_ESCALATION",
                description=(
                    f"After {self._max_consecutive_failures} consecutive failures across tools "
                    f"matching {self._monitored_patterns}, the run pauses for intervention."
                ),
                applies_to_patterns=self._monitored_patterns,
                max_consecutive_errors=self._max_consecutive_failures,
                on_exceeded="pause",
            ),
        )

    def handle_tool_call(self, tool_call: ToolCall) -> ToolCall | AgentPauseSignal:
        if not _is_tool_allowed(tool_call.tool_key, self._monitored_patterns):
            return tool_call
        if self._consecutive_failures < self._max_consecutive_failures:
            return tool_call
        return AgentPauseSignal(
            reason=(
                f"Error escalation triggered after {self._consecutive_failures} consecutive failures."
            ),
            details={
                "strategy": "error_escalation",
                "consecutive_failures": self._consecutive_failures,
                "recent_failures": list(self._recent_failures),
            },
        )

    def handle_tool_result(self, tool_call: ToolCall, result: ToolResult) -> ToolResult:
        if not _is_tool_allowed(tool_call.tool_key, self._monitored_patterns):
            return result
        if _is_error_result(result):
            self._consecutive_failures += 1
            self._recent_failures.append(
                {
                    "tool_key": tool_call.tool_key,
                    "arguments": dict(tool_call.arguments),
                }
            )
            self._recent_failures = self._recent_failures[-5:]
            return result
        self._consecutive_failures = 0
        self._recent_failures.clear()
        return result

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        lines = [
            f"Monitored patterns: {self._monitored_patterns}",
            f"Max consecutive failures before pause: {self._max_consecutive_failures}",
            f"Current consecutive failures: {self._consecutive_failures}",
            f"Recent failures tracked: {len(self._recent_failures)}",
        ]
        return (
            *super().get_parameter_sections(),
            AgentParameterSection(title=f"Behavior State: {self.layer_id}", content="\n".join(lines)),
        )


__all__ = ["ErrorEscalationBehavior"]
