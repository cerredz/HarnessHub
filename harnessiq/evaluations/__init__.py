"""Evaluation scaffolding for behavior-focused Harnessiq evals.

This package is intentionally separate from ``harnessiq.tools.eval``:
``harnessiq.tools.eval`` exposes agent-callable tool definitions, while
``harnessiq.evaluations`` provides repository-side primitives for defining,
grouping, and running evaluation checks over agent behavior.
"""

from .assertions import (
    duration_at_most,
    final_output_exists,
    metadata_has_keys,
    output_contains,
    output_contains_all,
    output_field_equals,
    output_matches_regex,
    solve_rate_at_least,
    step_count_at_most,
    tool_call_count_at_most,
    tool_called,
    tool_called_at_least,
    tool_called_exactly,
    tool_not_called,
    tools_called_in_order,
)
from .boilerplate import (
    CORRECTNESS_CATEGORY,
    EFFICIENCY_CATEGORY,
    OUTPUT_CATEGORY,
    TOOL_USE_CATEGORY,
    build_evaluation_case,
)
from .correctness import build_correctness_case
from .efficiency import build_efficiency_case
from .metrics import (
    build_metrics_snapshot,
    cost_efficiency_ratio,
    duration_efficiency_ratio,
    solve_rate,
    step_efficiency_ratio,
    tool_call_efficiency_ratio,
)
from .models import (
    EvaluationCheck,
    EvaluationCheckResult,
    EvaluationContext,
    EvaluationToolCall,
)
from .output import build_output_case
from .registry import EvaluationCase, EvaluationCaseResult, EvaluationRegistry, run_evaluation_case
from .tool_use import build_tool_use_case

__all__ = [
    "CORRECTNESS_CATEGORY",
    "EFFICIENCY_CATEGORY",
    "OUTPUT_CATEGORY",
    "TOOL_USE_CATEGORY",
    "EvaluationCase",
    "EvaluationCaseResult",
    "EvaluationCheck",
    "EvaluationCheckResult",
    "EvaluationContext",
    "EvaluationRegistry",
    "EvaluationToolCall",
    "build_correctness_case",
    "build_efficiency_case",
    "build_evaluation_case",
    "build_metrics_snapshot",
    "build_output_case",
    "build_tool_use_case",
    "cost_efficiency_ratio",
    "duration_at_most",
    "duration_efficiency_ratio",
    "final_output_exists",
    "metadata_has_keys",
    "output_contains",
    "output_contains_all",
    "output_field_equals",
    "output_matches_regex",
    "run_evaluation_case",
    "solve_rate",
    "solve_rate_at_least",
    "step_count_at_most",
    "step_efficiency_ratio",
    "tool_call_count_at_most",
    "tool_call_efficiency_ratio",
    "tool_called",
    "tool_called_at_least",
    "tool_called_exactly",
    "tool_not_called",
    "tools_called_in_order",
]
