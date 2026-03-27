"""Basic correctness and efficiency metrics for evaluation runs."""

from __future__ import annotations

from .models import EvaluationContext


def _efficiency_ratio(*, actual: float | int | None, expected: float | int | None) -> float | None:
    if actual is None or expected is None:
        return None
    if actual < 0 or expected < 0:
        raise ValueError("Efficiency ratios require non-negative actual and expected values.")
    if actual == 0:
        return 1.0 if expected == 0 else None
    return float(expected) / float(actual)


def solve_rate(context: EvaluationContext) -> float | None:
    """Return the expected-step-normalized solve rate for the run."""
    return step_efficiency_ratio(context)


def step_efficiency_ratio(context: EvaluationContext) -> float | None:
    """Compare expected steps against the observed step count."""
    return _efficiency_ratio(actual=context.step_count, expected=context.expected_step_count)


def tool_call_efficiency_ratio(context: EvaluationContext) -> float | None:
    """Compare expected tool calls against the observed tool-call count."""
    return _efficiency_ratio(actual=context.tool_call_count(), expected=context.expected_tool_calls)


def duration_efficiency_ratio(context: EvaluationContext) -> float | None:
    """Compare expected run duration against observed duration."""
    return _efficiency_ratio(actual=context.duration_seconds, expected=context.expected_duration_seconds)


def cost_efficiency_ratio(context: EvaluationContext) -> float | None:
    """Compare expected run cost against observed run cost."""
    return _efficiency_ratio(actual=context.cost_usd, expected=context.expected_cost_usd)


def build_metrics_snapshot(context: EvaluationContext) -> dict[str, float | None]:
    """Return the core metrics currently tracked by the scaffolding layer."""
    return {
        "solve_rate": solve_rate(context),
        "step_efficiency_ratio": step_efficiency_ratio(context),
        "tool_call_efficiency_ratio": tool_call_efficiency_ratio(context),
        "duration_efficiency_ratio": duration_efficiency_ratio(context),
        "cost_efficiency_ratio": cost_efficiency_ratio(context),
    }


__all__ = [
    "build_metrics_snapshot",
    "cost_efficiency_ratio",
    "duration_efficiency_ratio",
    "solve_rate",
    "step_efficiency_ratio",
    "tool_call_efficiency_ratio",
]
