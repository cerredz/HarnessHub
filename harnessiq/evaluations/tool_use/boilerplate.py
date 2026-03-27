"""Boilerplate constructors for tool-use evaluations."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from ..boilerplate import TOOL_USE_CATEGORY, build_evaluation_case
from ..models import EvaluationCheck
from ..registry import EvaluationCase


def build_tool_use_case(
    key: str,
    title: str,
    description: str,
    *,
    checks: Iterable[EvaluationCheck] = (),
    categories: Iterable[str] = (),
    metadata: Mapping[str, Any] | None = None,
) -> EvaluationCase:
    """Build a tool-use-first evaluation case."""
    return build_evaluation_case(
        key,
        title,
        description,
        categories=(TOOL_USE_CATEGORY, *categories),
        checks=checks,
        metadata=metadata,
    )


__all__ = ["build_tool_use_case"]
