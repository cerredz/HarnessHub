"""
===============================================================================
File: harnessiq/formalization/metrics/layer.py

What this file does:
- Implements MetricsLayer, a formalization layer that tracks declared metrics
  and surfaces them live in the context window.
- Deterministic metrics are updated silently by intercepting tool results.
- Model-reported metrics are updated when the model calls metrics.report().
- All metric values are durable — they survive context window resets via
  MetricStore (disk-backed JSON).

Use cases:
- Declare metrics to track agent activity quantitatively. Compose with
  StopCriteriaLayer to gate completion on measurable thresholds.

How to use it:
- Construct with one or more metric specs and pass to BaseAgent via
  formalization_layers= or the metrics= sugar parameter.

Intent:
- Give agents quantifiable, durable progress tracking that is always visible
  in the context window and always survives resets.
===============================================================================
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from harnessiq.formalization.base import BaseFormalizationLayer
from harnessiq.shared.agents import AgentParameterSection
from harnessiq.shared.formalization import LayerRuleRecord
from harnessiq.shared.tools import RegisteredTool, ToolResult

from .spec import DeterministicMetricSpec, MetricValueType, ModelReportedMetricSpec
from .store import MetricStore


class MetricsLayer(BaseFormalizationLayer):
    """Tracks declared metrics and surfaces them live in the context window.

    Deterministic metrics are updated silently by intercepting tool results.
    Model-reported metrics are updated when the model calls metrics.report().
    All metrics are durable — they survive context window resets.
    """

    def __init__(
        self,
        metrics: Sequence[DeterministicMetricSpec | ModelReportedMetricSpec],
    ) -> None:
        if not metrics:
            raise ValueError("MetricsLayer requires at least one metric spec.")
        seen: set[str] = set()
        for m in metrics:
            if m.name in seen:
                raise ValueError(f"Duplicate metric name '{m.name}'.")
            seen.add(m.name)

        self._deterministic = [m for m in metrics if isinstance(m, DeterministicMetricSpec)]
        self._model_reported = [m for m in metrics if isinstance(m, ModelReportedMetricSpec)]
        self._all_specs: dict[str, DeterministicMetricSpec | ModelReportedMetricSpec] = {
            m.name: m for m in metrics
        }
        self._store: MetricStore | None = None

    # ── Public API used by StopCriteriaLayer ──────────────────────────────────

    def get_value(self, metric_name: str) -> MetricValueType | None:
        """Return the current value of a named metric, or None if not yet initialized."""
        if self._store is None:
            return None
        spec = self._all_specs.get(metric_name)
        if spec is None:
            return None
        return self._store.get(metric_name, spec.initial_value)

    def all_values(self) -> dict[str, MetricValueType]:
        """Return a snapshot of all current metric values."""
        if self._store is None:
            return {}
        return {
            name: self._store.get(name, spec.initial_value)
            for name, spec in self._all_specs.items()
        }

    # ── Documentation ──────────────────────────────────────────────────────────

    @property
    def layer_id(self) -> str:
        return "MetricsLayer"

    def _describe_identity(self) -> str:
        parts: list[str] = []
        if self._deterministic:
            names = ", ".join(s.name for s in self._deterministic)
            parts.append(f"{len(self._deterministic)} auto-tracked metric(s): {names}")
        if self._model_reported:
            names = ", ".join(s.name for s in self._model_reported)
            parts.append(f"{len(self._model_reported)} self-reported metric(s): {names}")
        return (
            f"You are operating with tracked metrics: {'; '.join(parts)}. "
            f"All metrics are durable and survive context window resets. "
            f"Current values appear in the Metrics section below."
        )

    def _describe_contract(self) -> str:
        lines: list[str] = []
        if self._model_reported:
            lines.append(
                "The following metrics must be reported by you using "
                "metrics.report(name=..., value=...):"
            )
            for spec in self._model_reported:
                instructions = spec.report_instructions or (
                    f"Report '{spec.name}' ({spec.value_type}) whenever "
                    f"{spec.description.lower().rstrip('.')}."
                )
                lines.append(f"  {spec.name} ({spec.value_type}): {instructions}")
        if self._deterministic:
            lines.append(
                "\nThe following metrics are tracked automatically "
                "(you do not need to do anything):"
            )
            for spec in self._deterministic:
                lines.append(f"  {spec.name}: {spec.description}")
        return "\n".join(lines)

    def _describe_rules(self) -> tuple[LayerRuleRecord, ...]:
        rules: list[LayerRuleRecord] = []
        for spec in self._deterministic:
            patterns = ", ".join(spec.watch_tool_patterns)
            rules.append(
                LayerRuleRecord(
                    rule_id=f"METRIC-TRACK-{spec.name.upper()}",
                    description=(
                        f"on_tool_result watches [{patterns}] and calls "
                        f"extract_value. Non-None results update '{spec.name}' "
                        f"via aggregation='{spec.aggregation}'."
                    ),
                    enforced_at="on_tool_result",
                    enforcement_type="observe",
                )
            )
        if self._model_reported:
            rules.append(
                LayerRuleRecord(
                    rule_id="METRIC-REPORT-TOOL",
                    description=(
                        "metrics.report(name, value) is contributed to the executor. "
                        "When the model calls it with a declared model-reported metric "
                        "name, the value is validated and stored."
                    ),
                    enforced_at="on_tool_result",
                    enforcement_type="observe",
                )
            )
        return tuple(rules)

    def _describe_configuration(self) -> dict[str, Any]:
        return {
            "metric_count": len(self._all_specs),
            "metrics": [
                {
                    "name": m.name,
                    "type": (
                        "deterministic"
                        if isinstance(m, DeterministicMetricSpec)
                        else "model_reported"
                    ),
                    "description": m.description,
                    "aggregation": m.aggregation,
                    "initial_value": m.initial_value,
                    "visible": m.visible,
                    "unit": m.unit,
                }
                for m in self._all_specs.values()
            ],
        }

    # ── Context window — live metric values ───────────────────────────────────

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        base = super().get_parameter_sections()
        visible = [(name, spec) for name, spec in self._all_specs.items() if spec.visible]
        if not visible or self._store is None:
            return base

        lines: list[str] = []
        for name, spec in visible:
            value = self._store.get(name, spec.initial_value)
            unit = f" {spec.unit}" if spec.unit else ""
            kind = "auto" if isinstance(spec, DeterministicMetricSpec) else "self-reported"
            lines.append(f"{name}: {value}{unit}  ({spec.description}) [{kind}]")

        model_reported_visible = [s for s in self._model_reported if s.visible]
        if model_reported_visible:
            lines.append("")
            lines.append(
                'Report model-assessed metrics via: '
                'metrics.report(name="<metric_name>", value=<value>)'
            )

        return base + (AgentParameterSection(title="Metrics", content="\n".join(lines)),)

    # ── Tools ──────────────────────────────────────────────────────────────────

    def get_formalization_tools(self) -> tuple[RegisteredTool, ...]:
        """Contribute metrics.report tool when model-reported metrics are declared."""
        if not self._model_reported:
            return ()
        from .tools import build_metrics_report_tool
        return (build_metrics_report_tool(self),)

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def on_agent_prepare(self, *, agent_name: str, memory_path: str) -> None:
        """Initialize the metric store and seed any metrics not yet persisted."""
        del agent_name
        self._store = MetricStore(Path(memory_path))
        for name, spec in self._all_specs.items():
            if self._store.get(name, None) is None:
                self._store.set(name, spec.initial_value)

    def on_tool_result(self, result: ToolResult) -> ToolResult:
        """Auto-update deterministic metrics by inspecting tool results."""
        if self._store is None:
            return result

        from harnessiq.tools.hooks.defaults import is_tool_allowed

        for spec in self._deterministic:
            if not any(
                is_tool_allowed(result.tool_key, (p,))
                for p in spec.watch_tool_patterns
            ):
                continue
            args: dict[str, Any] = {}
            if hasattr(result, "arguments"):
                args = result.arguments or {}
            try:
                extracted = spec.extract_value(result.tool_key, args, result.output)
            except Exception:
                extracted = None
            if extracted is not None:
                self._store.apply_aggregation(
                    spec.name, extracted, spec.aggregation, spec.initial_value
                )

        return result

    def handle_model_report(self, name: str, value: Any) -> dict[str, Any]:
        """Called by the metrics.report tool handler to update a model-reported metric."""
        if self._store is None:
            return {"error": "MetricsLayer store is not initialized yet."}

        spec = self._all_specs.get(name)
        if spec is None or not isinstance(spec, ModelReportedMetricSpec):
            declared = [s.name for s in self._model_reported]
            return {
                "error": (
                    f"'{name}' is not a declared model-reported metric. "
                    f"Declared model-reported metrics: {declared}."
                )
            }

        type_map: dict[str, type | tuple[type, ...]] = {
            "int": int,
            "float": (int, float),
            "bool": bool,
            "string": str,
        }
        expected = type_map.get(spec.value_type, object)
        if not isinstance(value, expected):
            return {
                "error": (
                    f"Metric '{name}' expects {spec.value_type}, "
                    f"got {type(value).__name__}."
                )
            }

        updated = self._store.apply_aggregation(
            name, value, spec.aggregation, spec.initial_value
        )
        return {"metric": name, "value": updated, "status": "recorded"}
