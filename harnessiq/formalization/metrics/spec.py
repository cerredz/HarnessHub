"""
===============================================================================
File: harnessiq/formalization/metrics/spec.py

What this file does:
- Defines DeterministicMetricSpec and ModelReportedMetricSpec, the
  configuration dataclasses for metrics tracked by MetricsLayer.
- DeterministicMetricSpec: metric updated automatically by intercepting tool
  results via a user-provided extractor callable.
- ModelReportedMetricSpec: metric updated by the model calling metrics.report.

Use cases:
- Declare metrics to pass to MetricsLayer or BaseAgent(metrics=[...]).

How to use it:
- Import DeterministicMetricSpec or ModelReportedMetricSpec from
  harnessiq.formalization.metrics and pass one or more instances to
  MetricsLayer.

Intent:
- Keep metric configuration as frozen, self-validating dataclasses so metric
  declarations are explicit, inspectable, and immutable at runtime.
===============================================================================
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

MetricAggregation = Literal["increment", "set", "max", "min", "last"]
"""How a new measurement is merged into the current metric value.

"increment" — add the new value to the current (default for counts).
"set"       — replace the current value with the new value.
"max"       — keep whichever of current/new is larger.
"min"       — keep whichever of current/new is smaller.
"last"      — alias for "set", named semantically for time-series-like metrics.
"""

MetricValueType = int | float | bool | str


@dataclass(frozen=True, slots=True)
class DeterministicMetricSpec:
    """A metric whose value is updated automatically by intercepting tool results.

    The layer watches every tool result. When a result's tool key matches
    watch_tool_patterns, the layer calls extract_value with the tool key,
    its arguments, and its output. If extract_value returns a non-None value,
    the metric is updated using the declared aggregation.

    The model is never aware this tracking is happening.
    """

    name: str
    """Unique metric name. snake_case recommended."""

    description: str
    """What this metric measures. Shown to the model in the context window."""

    watch_tool_patterns: tuple[str, ...]
    """Tool key patterns to watch (fnmatch-style, e.g. 'terminal.*')."""

    extract_value: Callable[[str, dict[str, Any], Any], MetricValueType | None]
    """Callable extracting a measurement from one tool result.

    Signature: (tool_key: str, arguments: dict, output: Any) -> MetricValueType | None
    Return None to skip updating the metric for this result.
    """

    aggregation: MetricAggregation = "increment"
    """How new values are merged into the current metric value."""

    initial_value: MetricValueType = 0
    """Starting value before any updates."""

    visible: bool = True
    """Whether this metric appears in the context window parameter section."""

    unit: str = ""
    """Optional unit label displayed next to the value."""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("DeterministicMetricSpec name must not be blank.")
        if not self.description.strip():
            raise ValueError("DeterministicMetricSpec description must not be blank.")
        if not self.watch_tool_patterns:
            raise ValueError("DeterministicMetricSpec watch_tool_patterns must not be empty.")
        if not callable(self.extract_value):
            raise ValueError("DeterministicMetricSpec extract_value must be callable.")


@dataclass(frozen=True, slots=True)
class ModelReportedMetricSpec:
    """A metric whose value is updated by the model calling metrics.report().

    Use this for subjective or self-assessed metrics that the model itself
    must evaluate — confidence scores, perceived quality ratings, task
    completion percentage estimates.
    """

    name: str
    """Unique metric name."""

    description: str
    """What this metric measures."""

    value_type: Literal["int", "float", "bool", "string"] = "float"
    """Expected value type when the model reports this metric."""

    report_instructions: str = ""
    """Instructions telling the model when and how to report this metric.
    If blank, a default instruction is generated from description and value_type.
    """

    initial_value: MetricValueType = 0
    """Starting value before the model first reports."""

    aggregation: MetricAggregation = "set"
    """How model-reported values update the current value. Defaults to 'set'
    because model-reported metrics are typically assessments (current state).
    """

    visible: bool = True
    """Whether this metric appears in the context window."""

    unit: str = ""
    """Optional unit label displayed next to the value."""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("ModelReportedMetricSpec name must not be blank.")
        if not self.description.strip():
            raise ValueError("ModelReportedMetricSpec description must not be blank.")
