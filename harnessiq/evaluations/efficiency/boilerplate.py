"""Boilerplate constructors for efficiency evaluations."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from ..boilerplate import EFFICIENCY_CATEGORY, build_evaluation_case
from ..models import EvaluationCheck
from ..registry import EvaluationCase


def build_efficiency_case(
    key: str,
    title: str,
    description: str,
    *,
    checks: Iterable[EvaluationCheck] = (),
    categories: Iterable[str] = (),
    metadata: Mapping[str, Any] | None = None,
) -> EvaluationCase:
    """Build an efficiency-first evaluation case."""
    return build_evaluation_case(
        key,
        title,
        description,
        categories=(EFFICIENCY_CATEGORY, *categories),
        checks=checks,
        metadata=metadata,
    )


__all__ = ["build_efficiency_case"]
