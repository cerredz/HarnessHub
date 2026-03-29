"""Concrete self-critique reasoning behavior."""

from __future__ import annotations

from harnessiq.shared.agents import AgentParameterSection
from harnessiq.shared.tools import ToolResult

from .base import BaseReasoningBehaviorLayer, ReasoningRequirementSpec, _is_tool_allowed


class SelfCritiqueBehavior(BaseReasoningBehaviorLayer):
    """Require critique after significant outputs before further action."""

    def __init__(
        self,
        output_patterns: tuple[str, ...],
        blocked_until_critique: tuple[str, ...] = ("artifact.*", "control.mark_complete"),
        critique_patterns: tuple[str, ...] = ("reason.critique", "reasoning.self_critique"),
    ) -> None:
        self._output_patterns = tuple(output_patterns)
        self._blocked_patterns = tuple(blocked_until_critique)
        self._critique_patterns = tuple(critique_patterns)
        self._critique_pending = False
        self._last_output_tool: str | None = None
        self._last_critique_tool: str | None = None

    def get_reasoning_requirements(self) -> tuple[ReasoningRequirementSpec, ...]:
        return (
            ReasoningRequirementSpec(
                requirement_id="SELF_CRITIQUE_REQUIRED",
                description=(
                    f"After tools matching {self._output_patterns} produce a significant output, "
                    f"a critique tool matching {self._critique_patterns} must be called before "
                    f"tools matching {self._blocked_patterns} become visible again."
                ),
                before_patterns=self._blocked_patterns,
                required_reasoning_patterns=self._critique_patterns,
                reasoning_hint="Identify weaknesses, omissions, and incorrect assumptions in the output.",
            ),
        )

    def reasoning_satisfied_for(self, trigger_key: str) -> bool:
        if _is_tool_allowed(trigger_key, self._blocked_patterns):
            return not self._critique_pending
        return True

    def _on_reasoning_completed(
        self,
        tool_key: str,
        requirement: ReasoningRequirementSpec,
    ) -> None:
        del requirement
        self._critique_pending = False
        self._last_critique_tool = tool_key

    def on_tool_result(self, result: ToolResult) -> ToolResult:
        if _is_tool_allowed(result.tool_key, self._output_patterns):
            self._critique_pending = True
            self._last_output_tool = result.tool_key
        return super().on_tool_result(result)

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        content = "\n".join(
            [
                f"Critique pending: {'yes' if self._critique_pending else 'no'}",
                f"Output patterns: {self._output_patterns}",
                f"Blocked patterns: {self._blocked_patterns}",
                f"Last output tool: {self._last_output_tool or 'none'}",
                f"Last critique tool: {self._last_critique_tool or 'none'}",
            ]
        )
        return (
            *super().get_parameter_sections(),
            AgentParameterSection(title=f"Behavior State: {self.layer_id}", content=content),
        )
