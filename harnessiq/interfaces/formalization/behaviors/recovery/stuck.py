"""Concrete stuck-detection behavior."""

from __future__ import annotations

from harnessiq.shared.agents import AgentParameterSection
from harnessiq.shared.tools import ToolCall, ToolResult

from .base import BaseErrorRecoveryLayer, RecoveryStrategySpec, _fingerprint_arguments, _is_tool_allowed


class StuckDetectionBehavior(BaseErrorRecoveryLayer):
    """Detect repeated identical calls and force a different approach."""

    def __init__(
        self,
        *,
        threshold: int = 3,
        monitored_patterns: tuple[str, ...] = ("*",),
    ) -> None:
        if threshold <= 0:
            raise ValueError("threshold must be greater than zero.")
        self._threshold = threshold
        self._monitored_patterns = tuple(monitored_patterns)
        self._last_signature: tuple[str, str] | None = None
        self._repeat_count = 0
        self._last_blocked_call: dict[str, object] | None = None

    def get_recovery_strategies(self) -> tuple[RecoveryStrategySpec, ...]:
        return (
            RecoveryStrategySpec(
                strategy_id="STUCK_DETECTION",
                description=(
                    f"After {self._threshold} repeated identical calls matching {self._monitored_patterns}, "
                    "the next identical call is blocked until the agent changes tools or arguments."
                ),
                applies_to_patterns=self._monitored_patterns,
                max_consecutive_errors=self._threshold,
                on_exceeded="hide_tool",
            ),
        )

    def handle_tool_call(self, tool_call: ToolCall) -> ToolCall | ToolResult:
        if not _is_tool_allowed(tool_call.tool_key, self._monitored_patterns):
            self._last_signature = None
            self._repeat_count = 0
            return tool_call
        signature = (tool_call.tool_key, _fingerprint_arguments(tool_call.arguments))
        next_count = self._repeat_count + 1 if signature == self._last_signature else 1
        self._last_signature = signature
        self._repeat_count = next_count
        if next_count <= self._threshold:
            return tool_call
        self._last_blocked_call = {
            "tool_key": tool_call.tool_key,
            "arguments": dict(tool_call.arguments),
            "repeat_count": next_count,
        }
        return ToolResult(
            tool_key=tool_call.tool_key,
            output={
                "error": (
                    f"Stuck pattern detected for {tool_call.tool_key}. "
                    f"The same arguments were repeated {next_count} times."
                ),
                "strategy": "stuck_detection",
            },
        )

    def handle_tool_result(self, tool_call: ToolCall, result: ToolResult) -> ToolResult:
        del tool_call
        return result

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        lines = [
            f"Monitored patterns: {self._monitored_patterns}",
            f"Repeat threshold before blocking: {self._threshold}",
            f"Current repeat count: {self._repeat_count}",
            f"Last blocked call: {self._last_blocked_call or 'none'}",
        ]
        return (
            *super().get_parameter_sections(),
            AgentParameterSection(title=f"Behavior State: {self.layer_id}", content="\n".join(lines)),
        )


__all__ = ["StuckDetectionBehavior"]
