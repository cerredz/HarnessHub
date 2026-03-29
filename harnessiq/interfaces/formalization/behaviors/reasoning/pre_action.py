"""Concrete pre-action reasoning behavior."""

from __future__ import annotations

from harnessiq.shared.agents import AgentParameterSection
from harnessiq.shared.tools import ToolResult

from .base import BaseReasoningBehaviorLayer, ReasoningRequirementSpec, _is_tool_allowed


class PreActionReasoningBehavior(BaseReasoningBehaviorLayer):
    """Require a reasoning tool call before matching action tools appear."""

    def __init__(
        self,
        before_patterns: tuple[str, ...],
        reasoning_patterns: tuple[str, ...] = ("reason.*", "reasoning.*"),
        reasoning_hint: str = "",
    ) -> None:
        self._before_patterns = tuple(before_patterns)
        self._reasoning_patterns = tuple(reasoning_patterns)
        self._reasoning_hint = reasoning_hint
        self._reasoning_ready = False
        self._last_reasoning_tool: str | None = None

    def get_reasoning_requirements(self) -> tuple[ReasoningRequirementSpec, ...]:
        return (
            ReasoningRequirementSpec(
                requirement_id="PRE_ACTION_REASONING",
                description=(
                    f"Before tools matching {self._before_patterns} are called, a reasoning tool "
                    f"matching {self._reasoning_patterns} must be called first."
                ),
                before_patterns=self._before_patterns,
                required_reasoning_patterns=self._reasoning_patterns,
                reasoning_hint=self._reasoning_hint,
            ),
        )

    def reasoning_satisfied_for(self, trigger_key: str) -> bool:
        if _is_tool_allowed(trigger_key, self._before_patterns):
            return self._reasoning_ready
        return True

    def _on_reasoning_completed(
        self,
        tool_key: str,
        requirement: ReasoningRequirementSpec,
    ) -> None:
        del requirement
        self._reasoning_ready = True
        self._last_reasoning_tool = tool_key

    def on_tool_result(self, result: ToolResult) -> ToolResult:
        if _is_tool_allowed(result.tool_key, self._before_patterns):
            self._reasoning_ready = False
        return super().on_tool_result(result)

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        content = "\n".join(
            [
                f"Reasoning ready: {'yes' if self._reasoning_ready else 'no'}",
                f"Action patterns: {self._before_patterns}",
                f"Reasoning patterns: {self._reasoning_patterns}",
                f"Last reasoning tool: {self._last_reasoning_tool or 'none'}",
            ]
        )
        return (
            *super().get_parameter_sections(),
            AgentParameterSection(title=f"Behavior State: {self.layer_id}", content=content),
        )
