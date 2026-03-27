"""Boilerplate constructors for correctness evaluations."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from ..boilerplate import CORRECTNESS_CATEGORY, build_evaluation_case
from ..models import EvaluationCheck
from ..registry import EvaluationCase


def build_correctness_case(
    key: str,
    title: str,
    description: str,
    *,
    checks: Iterable[EvaluationCheck] = (),
    categories: Iterable[str] = (),
    metadata: Mapping[str, Any] | None = None,
) -> EvaluationCase:
    """Build a correctness-first evaluation case."""
    return build_evaluation_case(
        key,
        title,
        description,
        categories=(CORRECTNESS_CATEGORY, *categories),
        checks=checks,
        metadata=metadata,
    )


__all__ = ["build_correctness_case"]
