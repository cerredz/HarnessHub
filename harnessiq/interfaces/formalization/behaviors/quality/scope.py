"""Concrete scope-enforcement behavior."""

from __future__ import annotations

from collections.abc import Sequence

from harnessiq.shared.agents import AgentParameterSection
from harnessiq.toolset import define_tool

from .base import BaseQualityBehaviorLayer, QualityCriterionSpec


class ScopeEnforcementBehavior(BaseQualityBehaviorLayer):
    """Declare scope boundaries and record explicit scope-violation signals."""

    FLAG_SCOPE_VIOLATION_TOOL = "behavior.flag_scope_violation"

    def __init__(
        self,
        *,
        in_scope: Sequence[str],
        out_of_scope: Sequence[str],
    ) -> None:
        self._in_scope = tuple(str(item) for item in in_scope if str(item).strip())
        self._out_of_scope = tuple(str(item) for item in out_of_scope if str(item).strip())
        self._violations: list[dict[str, str]] = []

    def get_quality_criteria(self) -> tuple[QualityCriterionSpec, ...]:
        return (
            QualityCriterionSpec(
                criterion_id="SCOPE_ENFORCEMENT",
                description=(
                    "Stay within the declared scope boundaries. If the task drifts out of scope, "
                    "record the violation with behavior.flag_scope_violation."
                ),
            ),
        )

    def evaluate_criterion(
        self,
        criterion: QualityCriterionSpec,
        agent_state: dict[str, object],
    ) -> tuple[bool, str]:
        del criterion
        violations = agent_state.get("violations", [])
        if not violations:
            return True, ""
        return False, "Out-of-scope work was flagged and remains unresolved."

    def _build_agent_state(self) -> dict[str, object]:
        return {
            "in_scope": list(self._in_scope),
            "out_of_scope": list(self._out_of_scope),
            "violations": list(self._violations),
        }

    def get_formalization_tools(self):
        return (
            define_tool(
                key=self.FLAG_SCOPE_VIOLATION_TOOL,
                description="Record that the current request or next action is out of scope.",
                parameters={
                    "topic": {"type": "string", "description": "The out-of-scope topic or request."},
                    "reason": {"type": "string", "description": "Why it is outside the declared scope."},
                },
                required=["topic", "reason"],
                handler=self._handle_scope_violation,
            ),
        )

    def _handle_scope_violation(self, arguments: dict[str, object]) -> dict[str, object]:
        violation = {
            "topic": str(arguments["topic"]),
            "reason": str(arguments["reason"]),
        }
        self._violations.append(violation)
        return {"recorded": True, **violation}

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        lines = [
            "In scope:",
            *(f"- {item}" for item in self._in_scope),
            "",
            "Out of scope:",
            *(f"- {item}" for item in self._out_of_scope),
            "",
            f"Recorded scope violations: {len(self._violations)}",
        ]
        return (
            *super().get_parameter_sections(),
            AgentParameterSection(title=f"Behavior State: {self.layer_id}", content="\n".join(lines)),
        )
