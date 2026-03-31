"""
===============================================================================
File: harnessiq/formalization/criteria/expression.py

What this file does:
- Defines CriteriaExpression, the abstract base for combining stop criteria
  with AND/OR logic.
- Provides three concrete expression types:
    SingleCriterion — wraps one StopCriterion
    AndCriteria     — all children must pass
    OrCriteria      — at least one child must pass

Use cases:
- Build criterion trees and pass to StopCriteriaLayer(expression=...).

Intent:
- Keep composition logic in a dedicated module so the layer stays focused on
  lifecycle management.
===============================================================================
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from collections.abc import Sequence

from .criterion import StopCriterion


class CriteriaExpression(ABC):
    """Abstract expression that can combine multiple criteria with AND/OR logic."""

    @abstractmethod
    def is_satisfied(self) -> bool:
        """Return True if the expression currently passes."""

    @abstractmethod
    def failing_criteria(self) -> list[StopCriterion]:
        """Return all leaf criteria that are currently not satisfied."""

    @abstractmethod
    def all_criteria(self) -> list[StopCriterion]:
        """Return every leaf criterion in the expression tree."""


@dataclass
class SingleCriterion(CriteriaExpression):
    """Wraps one StopCriterion as a CriteriaExpression."""

    criterion: StopCriterion

    def is_satisfied(self) -> bool:
        return self.criterion.is_satisfied()

    def failing_criteria(self) -> list[StopCriterion]:
        return [] if self.criterion.is_satisfied() else [self.criterion]

    def all_criteria(self) -> list[StopCriterion]:
        return [self.criterion]


@dataclass
class AndCriteria(CriteriaExpression):
    """All child expressions must pass."""

    children: Sequence[CriteriaExpression]

    def is_satisfied(self) -> bool:
        return all(c.is_satisfied() for c in self.children)

    def failing_criteria(self) -> list[StopCriterion]:
        failing: list[StopCriterion] = []
        for child in self.children:
            failing.extend(child.failing_criteria())
        return failing

    def all_criteria(self) -> list[StopCriterion]:
        result: list[StopCriterion] = []
        for child in self.children:
            result.extend(child.all_criteria())
        return result


@dataclass
class OrCriteria(CriteriaExpression):
    """At least one child expression must pass."""

    children: Sequence[CriteriaExpression]

    def is_satisfied(self) -> bool:
        return any(c.is_satisfied() for c in self.children)

    def failing_criteria(self) -> list[StopCriterion]:
        # An OR expression only fails if ALL children fail.
        if self.is_satisfied():
            return []
        failing: list[StopCriterion] = []
        for child in self.children:
            failing.extend(child.failing_criteria())
        return failing

    def all_criteria(self) -> list[StopCriterion]:
        result: list[StopCriterion] = []
        for child in self.children:
            result.extend(child.all_criteria())
        return result
