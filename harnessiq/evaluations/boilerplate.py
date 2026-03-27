"""High-signal builders for future evaluation cases."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .models import EvaluationCheck
from .registry import EvaluationCase

CORRECTNESS_CATEGORY = "correctness"
TOOL_USE_CATEGORY = "tool_use"
EFFICIENCY_CATEGORY = "efficiency"
OUTPUT_CATEGORY = "output"


def build_evaluation_case(
    key: str,
    title: str,
    description: str,
    *,
    categories: Iterable[str],
    checks: Iterable[EvaluationCheck] = (),
    metadata: Mapping[str, Any] | None = None,
) -> EvaluationCase:
    """Build one evaluation case with normalized metadata and categories."""
    return EvaluationCase(
        key=key,
        title=title,
        description=description,
        categories=tuple(categories),
        checks=tuple(checks),
        metadata=dict(metadata or {}),
    )


__all__ = [
    "CORRECTNESS_CATEGORY",
    "EFFICIENCY_CATEGORY",
    "OUTPUT_CATEGORY",
    "TOOL_USE_CATEGORY",
    "build_evaluation_case",
]
