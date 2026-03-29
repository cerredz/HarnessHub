"""Concrete competing-hypothesis behavior."""

from __future__ import annotations

from harnessiq.shared.agents import AgentParameterSection
from harnessiq.shared.tools import ToolResult

from .base import BaseReasoningBehaviorLayer, ReasoningRequirementSpec, _is_tool_allowed


class HypothesisTestingBehavior(BaseReasoningBehaviorLayer):
    """Require hypothesis generation and testing before committing conclusions."""

    def __init__(
        self,
        commit_patterns: tuple[str, ...],
        hypothesis_patterns: tuple[str, ...] = ("reason.brainstorm", "reasoning.hypothesis_generation"),
        testing_patterns: tuple[str, ...] = ("reason.critique", "reasoning.falsification_test"),
    ) -> None:
        self._commit_patterns = tuple(commit_patterns)
        self._hypothesis_patterns = tuple(hypothesis_patterns)
        self._testing_patterns = tuple(testing_patterns)
        self._generated = False
        self._tested = False

    def get_reasoning_requirements(self) -> tuple[ReasoningRequirementSpec, ...]:
        return (
            ReasoningRequirementSpec(
                requirement_id="HYPOTHESIS_TESTING_REQUIRED",
                description=(
                    f"Before tools matching {self._commit_patterns} are called, the agent must "
                    f"generate competing hypotheses with {self._hypothesis_patterns} and test "
                    f"them with {self._testing_patterns}."
                ),
                before_patterns=self._commit_patterns,
                required_reasoning_patterns=(
                    *self._hypothesis_patterns,
                    *self._testing_patterns,
                ),
                reasoning_hint="Generate multiple explanations and test them before committing.",
            ),
        )

    def reasoning_satisfied_for(self, trigger_key: str) -> bool:
        if _is_tool_allowed(trigger_key, self._commit_patterns):
            return self._generated and self._tested
        return True

    def _on_reasoning_completed(
        self,
        tool_key: str,
        requirement: ReasoningRequirementSpec,
    ) -> None:
        del requirement
        if any(_is_tool_allowed(tool_key, (pattern,)) for pattern in self._hypothesis_patterns):
            self._generated = True
        if any(_is_tool_allowed(tool_key, (pattern,)) for pattern in self._testing_patterns):
            self._tested = True

    def on_tool_result(self, result: ToolResult) -> ToolResult:
        if _is_tool_allowed(result.tool_key, self._commit_patterns):
            self._generated = False
            self._tested = False
        return super().on_tool_result(result)

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        content = "\n".join(
            [
                f"Hypotheses generated: {'yes' if self._generated else 'no'}",
                f"Hypotheses tested: {'yes' if self._tested else 'no'}",
                f"Commit patterns: {self._commit_patterns}",
            ]
        )
        return (
            *super().get_parameter_sections(),
            AgentParameterSection(title=f"Behavior State: {self.layer_id}", content=content),
        )
