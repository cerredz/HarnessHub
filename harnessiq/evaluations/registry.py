"""Registration and execution helpers for evaluation cases."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from .metrics import build_metrics_snapshot
from .models import EvaluationCheck, EvaluationCheckResult, EvaluationContext


def _normalize_categories(categories: Iterable[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for category in categories:
        stripped = category.strip()
        if not stripped:
            raise ValueError("Evaluation categories must not be blank.")
        if stripped in seen:
            continue
        seen.add(stripped)
        normalized.append(stripped)
    if not normalized:
        raise ValueError("Evaluation cases must include at least one category.")
    return tuple(normalized)


@dataclass(frozen=True, slots=True)
class EvaluationCase:
    """Metadata plus composable checks for one evaluation case."""

    key: str
    title: str
    description: str
    categories: tuple[str, ...]
    checks: tuple[EvaluationCheck, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError("EvaluationCase key must not be blank.")
        if not self.title.strip():
            raise ValueError("EvaluationCase title must not be blank.")
        if not self.description.strip():
            raise ValueError("EvaluationCase description must not be blank.")
        object.__setattr__(self, "categories", _normalize_categories(self.categories))
        object.__setattr__(self, "checks", tuple(self.checks))
        object.__setattr__(self, "metadata", dict(self.metadata))


@dataclass(frozen=True, slots=True)
class EvaluationCaseResult:
    """Structured result from executing a case against one context."""

    case: EvaluationCase
    check_results: tuple[EvaluationCheckResult, ...]
    metrics: dict[str, float | None]

    @property
    def passed(self) -> bool:
        return all(result.passed for result in self.check_results)

    @property
    def pass_rate(self) -> float:
        if not self.check_results:
            return 1.0
        passed_count = sum(1 for result in self.check_results if result.passed)
        return passed_count / len(self.check_results)


def run_evaluation_case(case: EvaluationCase, context: EvaluationContext) -> EvaluationCaseResult:
    """Execute every check in ``case`` against ``context``."""
    check_results = tuple(check(context) for check in case.checks)
    return EvaluationCaseResult(case=case, check_results=check_results, metrics=build_metrics_snapshot(context))


class EvaluationRegistry:
    """Simple in-memory registry for evaluation cases."""

    def __init__(self) -> None:
        self._cases: dict[str, EvaluationCase] = {}

    def register_case(self, case: EvaluationCase) -> EvaluationCase:
        if case.key in self._cases:
            raise ValueError(f"Evaluation case {case.key!r} is already registered.")
        self._cases[case.key] = case
        return case

    def register_cases(self, *cases: EvaluationCase) -> tuple[EvaluationCase, ...]:
        return tuple(self.register_case(case) for case in cases)

    def get_case(self, key: str) -> EvaluationCase:
        try:
            return self._cases[key]
        except KeyError as exc:
            raise KeyError(f"Unknown evaluation case {key!r}.") from exc

    def list_cases(self) -> tuple[EvaluationCase, ...]:
        return tuple(self._cases.values())

    def cases_for_category(self, category: str) -> tuple[EvaluationCase, ...]:
        return tuple(case for case in self._cases.values() if category in case.categories)


__all__ = [
    "EvaluationCase",
    "EvaluationCaseResult",
    "EvaluationRegistry",
    "run_evaluation_case",
]
