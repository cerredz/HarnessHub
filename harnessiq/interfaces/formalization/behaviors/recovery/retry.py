"""Concrete retry-strategy behavior."""

from __future__ import annotations

from harnessiq.shared.agents import AgentParameterSection
from harnessiq.shared.tools import ToolCall, ToolResult

from .base import (
    BaseErrorRecoveryLayer,
    RecoveryStrategySpec,
    _fingerprint_arguments,
    _is_error_result,
    _is_tool_allowed,
)


class RetryStrategyBehavior(BaseErrorRecoveryLayer):
    """Block repeated failing calls that reuse the same arguments."""

    def __init__(
        self,
        *,
        monitored_patterns: tuple[str, ...],
        max_retries: int = 2,
    ) -> None:
        if max_retries <= 0:
            raise ValueError("max_retries must be greater than zero.")
        self._monitored_patterns = tuple(monitored_patterns)
        self._max_retries = max_retries
        self._failure_counts: dict[tuple[str, str], int] = {}
        self._failure_history: list[dict[str, object]] = []
        self._last_blocked_call: dict[str, object] | None = None

    def get_recovery_strategies(self) -> tuple[RecoveryStrategySpec, ...]:
        return (
            RecoveryStrategySpec(
                strategy_id="RETRY_STRATEGY",
                description=(
                    f"Calls matching {self._monitored_patterns} may fail with the same arguments "
                    f"at most {self._max_retries} time(s) before the next identical attempt is blocked."
                ),
                applies_to_patterns=self._monitored_patterns,
                max_consecutive_errors=self._max_retries,
                on_exceeded="hide_tool",
            ),
        )

    def handle_tool_call(self, tool_call: ToolCall) -> ToolCall | ToolResult:
        if not _is_tool_allowed(tool_call.tool_key, self._monitored_patterns):
            return tool_call
        fingerprint = _fingerprint_arguments(tool_call.arguments)
        count = self._failure_counts.get((tool_call.tool_key, fingerprint), 0)
        if count < self._max_retries:
            return tool_call
        self._last_blocked_call = {
            "tool_key": tool_call.tool_key,
            "arguments": dict(tool_call.arguments),
            "failures": count,
        }
        return ToolResult(
            tool_key=tool_call.tool_key,
            output={
                "error": (
                    f"Retry limit reached for {tool_call.tool_key} with the same arguments. "
                    "Change the arguments or try a different approach."
                ),
                "strategy": "retry",
            },
        )

    def handle_tool_result(self, tool_call: ToolCall, result: ToolResult) -> ToolResult:
        if not _is_tool_allowed(tool_call.tool_key, self._monitored_patterns):
            return result
        fingerprint = _fingerprint_arguments(tool_call.arguments)
        key = (tool_call.tool_key, fingerprint)
        if _is_error_result(result):
            next_count = self._failure_counts.get(key, 0) + 1
            self._failure_counts[key] = next_count
            self._failure_history.append(
                {
                    "tool_key": tool_call.tool_key,
                    "arguments": dict(tool_call.arguments),
                    "failures": next_count,
                }
            )
            self._failure_history = self._failure_history[-5:]
            return result
        self._failure_counts.pop(key, None)
        return result

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        lines = [
            f"Monitored patterns: {self._monitored_patterns}",
            f"Max retries per identical call: {self._max_retries}",
            f"Tracked failing call fingerprints: {len(self._failure_counts)}",
            f"Last blocked call: {self._last_blocked_call or 'none'}",
        ]
        return (
            *super().get_parameter_sections(),
            AgentParameterSection(title=f"Behavior State: {self.layer_id}", content="\n".join(lines)),
        )


__all__ = ["RetryStrategyBehavior"]
