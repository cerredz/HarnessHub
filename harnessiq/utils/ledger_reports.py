"""Ledger reporting helpers."""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from harnessiq.utils.ledger_models import LedgerEntry


def build_ledger_report(entries: Sequence[LedgerEntry]) -> dict[str, Any]:
    summary: dict[str, dict[str, Any]] = {}
    total_resets = 0
    total_seconds = 0.0
    for entry in entries:
        bucket = summary.setdefault(
            entry.agent_name,
            {
                "agent_name": entry.agent_name,
                "runs": 0,
                "statuses": {},
                "output_metrics": {},
                "total_resets": 0,
                "total_duration_seconds": 0.0,
            },
        )
        bucket["runs"] += 1
        bucket["total_resets"] += entry.reset_count
        total_resets += entry.reset_count
        duration_seconds = max(0.0, (entry.finished_at - entry.started_at).total_seconds())
        bucket["total_duration_seconds"] += duration_seconds
        total_seconds += duration_seconds

        status_counts = bucket["statuses"]
        status_counts[entry.status] = int(status_counts.get(entry.status, 0)) + 1

        output_metrics = bucket["output_metrics"]
        for key, value in _count_output_metrics(entry.outputs).items():
            output_metrics[key] = int(output_metrics.get(key, 0)) + value

    return {
        "agents": [summary[name] for name in sorted(summary)],
        "total_resets": total_resets,
        "total_runs": len(entries),
        "average_duration_seconds": (total_seconds / len(entries)) if entries else 0.0,
    }


def render_ledger_report(report: Mapping[str, Any], *, output_format: str = "markdown") -> str:
    normalized = output_format.strip().lower()
    if normalized == "json":
        return json.dumps(report, indent=2, sort_keys=True)
    if normalized != "markdown":
        raise ValueError(f"Unsupported report format '{output_format}'.")
    lines = ["# HarnessIQ Run Report", ""]
    for agent in report.get("agents", []):
        agent_name = str(agent["agent_name"])
        lines.append(f"## {agent_name}")
        lines.append(f"- Runs: {agent['runs']}")
        lines.append(f"- Statuses: {json.dumps(agent['statuses'], sort_keys=True)}")
        metrics = agent.get("output_metrics", {})
        if metrics:
            lines.append(f"- Output metrics: {json.dumps(metrics, sort_keys=True)}")
        lines.append(f"- Total resets: {agent['total_resets']}")
        lines.append(f"- Total duration seconds: {round(float(agent['total_duration_seconds']), 2)}")
        lines.append("")
    lines.append(f"Total runs: {report.get('total_runs', 0)}")
    lines.append(f"Total resets: {report.get('total_resets', 0)}")
    lines.append(f"Average duration seconds: {round(float(report.get('average_duration_seconds', 0.0)), 2)}")
    return "\n".join(lines).rstrip()


def _count_output_metrics(outputs: Mapping[str, Any]) -> dict[str, int]:
    metrics: dict[str, int] = {}
    for key, value in outputs.items():
        if isinstance(value, list):
            metrics[key] = len(value)
        elif isinstance(value, dict) and "count" in value and isinstance(value["count"], int):
            metrics[key] = int(value["count"])
    return metrics


__all__ = [
    "build_ledger_report",
    "render_ledger_report",
]
