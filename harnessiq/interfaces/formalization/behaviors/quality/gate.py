"""Concrete generic quality-gate behavior."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from harnessiq.shared.agents import AgentParameterSection

from .base import BaseQualityBehaviorLayer, QualityCriterionSpec

QualityEvaluator = Callable[[QualityCriterionSpec, dict[str, Any]], tuple[bool, str]]
QualityStateBuilder = Callable[[], dict[str, Any]]


class QualityGateBehavior(BaseQualityBehaviorLayer):
    """Evaluate explicit Python quality criteria before completion."""

    def __init__(
        self,
        *,
        criteria: Sequence[QualityCriterionSpec],
        evaluator: QualityEvaluator,
        state_builder: QualityStateBuilder | None = None,
        configuration: Mapping[str, Any] | None = None,
    ) -> None:
        self._criteria = tuple(criteria)
        self._evaluator = evaluator
        self._state_builder = state_builder
        self._configuration = dict(configuration or {})

    def get_quality_criteria(self) -> tuple[QualityCriterionSpec, ...]:
        return self._criteria

    def evaluate_criterion(
        self,
        criterion: QualityCriterionSpec,
        agent_state: dict[str, Any],
    ) -> tuple[bool, str]:
        return self._evaluator(criterion, agent_state)

    def _build_agent_state(self) -> dict[str, Any]:
        if self._state_builder is None:
            return {}
        return dict(self._state_builder())

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        lines = ["Quality criteria:"]
        for criterion in self._criteria:
            lines.append(f"- {criterion.criterion_id}: {criterion.description}")
        if self._configuration:
            lines.extend(["", f"Configuration: {self._configuration}"])
        return (
            *super().get_parameter_sections(),
            AgentParameterSection(title=f"Behavior State: {self.layer_id}", content="\n".join(lines)),
        )
