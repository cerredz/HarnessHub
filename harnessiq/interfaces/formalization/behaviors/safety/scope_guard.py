"""Concrete scope-guard behavior."""

from __future__ import annotations

from harnessiq.shared.agents import AgentParameterSection
from harnessiq.shared.tools import ToolCall, ToolResult

from .base import BaseSafetyBehaviorLayer, GuardrailSpec


class ScopeGuardBehavior(BaseSafetyBehaviorLayer):
    """Block protected tools when their arguments point outside declared scope."""

    def __init__(
        self,
        *,
        guarded_patterns: tuple[str, ...],
        argument_block_patterns: tuple[tuple[str, str], ...],
    ) -> None:
        self._guarded_patterns = tuple(guarded_patterns)
        self._argument_block_patterns = tuple(argument_block_patterns)
        self._last_blocked_call: dict[str, object] | None = None

    def get_guardrails(self) -> tuple[GuardrailSpec, ...]:
        return (
            GuardrailSpec(
                guardrail_id="SCOPE_GUARD",
                description=(
                    f"Tools matching {self._guarded_patterns} are blocked when arguments match "
                    f"forbidden scope patterns {self._argument_block_patterns}."
                ),
                protected_patterns=self._guarded_patterns,
                argument_block_patterns=self._argument_block_patterns,
            ),
        )

    def is_guardrail_satisfied(self, guardrail: GuardrailSpec, tool_key: str) -> bool:
        del guardrail, tool_key
        return True

    def on_tool_call(self, tool_call: ToolCall) -> ToolCall | ToolResult:
        response = super().on_tool_call(tool_call)
        if isinstance(response, ToolResult):
            self._last_blocked_call = {
                "tool_key": tool_call.tool_key,
                "arguments": dict(tool_call.arguments),
            }
        return response

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        lines = [
            f"Guarded patterns: {self._guarded_patterns}",
            f"Argument block patterns: {self._argument_block_patterns}",
            f"Last blocked call: {self._last_blocked_call or 'none'}",
        ]
        return (
            *super().get_parameter_sections(),
            AgentParameterSection(title=f"Behavior State: {self.layer_id}", content="\n".join(lines)),
        )


__all__ = ["ScopeGuardBehavior"]
