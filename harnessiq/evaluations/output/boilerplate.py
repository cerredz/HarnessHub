"""Boilerplate constructors for output-oriented evaluations."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from ..boilerplate import OUTPUT_CATEGORY, build_evaluation_case
from ..models import EvaluationCheck
from ..registry import EvaluationCase


def build_output_case(
    key: str,
    title: str,
    description: str,
    *,
    checks: Iterable[EvaluationCheck] = (),
    categories: Iterable[str] = (),
    metadata: Mapping[str, Any] | None = None,
) -> EvaluationCase:
    """Build an output-quality-first evaluation case."""
    return build_evaluation_case(
        key,
        title,
        description,
        categories=(OUTPUT_CATEGORY, *categories),
        checks=checks,
        metadata=metadata,
    )


__all__ = ["build_output_case"]
