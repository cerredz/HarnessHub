"""
===============================================================================
File: harnessiq/formalization/metrics/tools.py

What this file does:
- Builds the metrics.report RegisteredTool that allows the model to explicitly
  update model-reported metric values.
- The tool is contributed to the agent's executor by MetricsLayer when at least
  one ModelReportedMetricSpec is declared.

Use cases:
- Used internally by MetricsLayer.get_formalization_tools(). Not intended for
  direct use by agent code.

Intent:
- Keep the tool definition and handler factory in a dedicated module so the
  layer implementation stays focused on lifecycle management.
===============================================================================
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from harnessiq.shared.tools import RegisteredTool, ToolDefinition

if TYPE_CHECKING:
    from .layer import MetricsLayer

METRICS_REPORT_KEY = "metrics.report"


def build_metrics_report_tool(layer: MetricsLayer) -> RegisteredTool:
    """Build the metrics.report tool bound to a MetricsLayer instance."""
    definition = ToolDefinition(
        key=METRICS_REPORT_KEY,
        name="report",
        description=(
            "Report the current value of a self-assessed or model-reported metric. "
            "Call this whenever your assessment of a declared metric has changed. "
            "Only metrics declared as model-reported can be updated this way."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The metric name, exactly as declared.",
                },
                "value": {
                    "description": "The current metric value.",
                },
            },
            "required": ["name", "value"],
            "additionalProperties": False,
        },
    )
    return RegisteredTool(
        definition=definition,
        handler=lambda args: _handle_report(layer, args),
    )


def _handle_report(layer: MetricsLayer, args: dict[str, Any]) -> dict[str, Any]:
    return layer.handle_model_report(str(args["name"]), args["value"])
