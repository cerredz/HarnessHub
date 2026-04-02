"""
===============================================================================
File: harnessiq/formalization/criteria/layer.py

What this file does:
- Implements StopCriteriaLayer, a formalization layer that prevents the agent
  from stopping until all declared success conditions are satisfied.
- Intercepts two stop signals:
    1. control.mark_complete tool calls — via on_tool_result
    2. should_continue=False model responses — via allow_completion()
- When criteria are not met, injects an error message listing failing criteria
  and their current progress so the model can understand what to do next.

Use cases:
- Compose with MetricsLayer to gate completion on measurable thresholds.
- Use standalone for artifact- or file-based completion gates.

Intent:
- Give agents a deterministic, model-visible contract for when they are
  allowed to stop — one that cannot be circumvented by the model simply
  deciding it is done.
===============================================================================
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from harnessiq.formalization.base import BaseFormalizationLayer
from harnessiq.shared.agents import AgentParameterSection
from harnessiq.shared.formalization import LayerRuleRecord
from harnessiq.shared.tools import CONTROL_MARK_COMPLETE, ToolResult

from .expression import CriteriaExpression


class StopCriteriaLayer(BaseFormalizationLayer):
    """Prevents the agent from stopping until all declared success conditions pass.

    Intercepts control.mark_complete via on_tool_result AND intercepts
    should_continue=False via the allow_completion() hook.

    When criteria are not met, injects an error message and current progress
    into the transcript so the model understands what it still needs to do.
    """

    def __init__(self, expression: CriteriaExpression) -> None:
        self._expression = expression

    @property
    def layer_id(self) -> str:
        return "StopCriteriaLayer"

    # ── Documentation ──────────────────────────────────────────────────────────

    def _describe_identity(self) -> str:
        total = len(self._expression.all_criteria())
        noun = "criterion" if total == 1 else "criteria"
        return (
            f"You are operating under {total} stop {noun} that must "
            f"all be satisfied before you are allowed to complete the run. "
            f"Attempts to stop prematurely are blocked and the unmet criteria "
            f"are shown to you so you can continue working."
        )

    def _describe_contract(self) -> str:
        lines = ["The following conditions must be true before the run can end:", ""]
        for c in self._expression.all_criteria():
            lines.append(f"  [{c.criterion_id}] {c.description}")
        return "\n".join(lines)

    def _describe_rules(self) -> tuple[LayerRuleRecord, ...]:
        return (
            LayerRuleRecord(
                rule_id="STOP-GATE-MARK-COMPLETE",
                description=(
                    "control.mark_complete is intercepted in on_tool_result. "
                    "If any criterion fails, the result is replaced with an error "
                    "payload listing which criteria are unmet and their current progress."
                ),
                enforced_at="on_tool_result",
                enforcement_type="block_result",
            ),
            LayerRuleRecord(
                rule_id="STOP-GATE-SHOULD-CONTINUE",
                description=(
                    "should_continue=False from the model response is intercepted via "
                    "allow_completion(). If any criterion fails, a synthetic error is "
                    "injected into the transcript and the run continues."
                ),
                enforced_at="allow_completion",
                enforcement_type="block_result",
            ),
        )

    def _describe_configuration(self) -> dict[str, Any]:
        return {
            "criterion_count": len(self._expression.all_criteria()),
            "criteria": [
                {
                    "id": c.criterion_id,
                    "description": c.description,
                    "currently_satisfied": c.is_satisfied(),
                    "progress": c.progress(),
                }
                for c in self._expression.all_criteria()
            ],
        }

    # ── Context window ─────────────────────────────────────────────────────────

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        base = super().get_parameter_sections()
        lines = ["Success criteria (must ALL pass before stopping):", ""]
        for c in self._expression.all_criteria():
            status = "\u2713 satisfied" if c.is_satisfied() else "\u2717 not yet met"
            lines.append(f"[{c.criterion_id}]  [{status}]")
            lines.append(f"  {c.description}")
            lines.append(f"  Progress: {c.progress()}")
            lines.append("")
        return base + (
            AgentParameterSection(
                title="Stop Criteria",
                content="\n".join(lines).rstrip(),
            ),
        )

    def get_template_sections(self) -> tuple[AgentParameterSection, ...]:
        base = super().get_template_sections()
        lines = ["Stop criteria (must ALL pass before stopping):", ""]
        for criterion in self._expression.all_criteria():
            lines.append(f"[{criterion.criterion_id}] {criterion.description}")
            lines.append("Progress at runtime: [will be shown during run]")
            lines.append("")
        return base + (
            AgentParameterSection(
                title="Stop Criteria",
                content="\n".join(lines).rstrip(),
            ),
        )

    # ── Enforcement ────────────────────────────────────────────────────────────

    def on_tool_result(self, result: ToolResult) -> ToolResult:
        """Block control.mark_complete when criteria are unmet (STOP-GATE-MARK-COMPLETE)."""
        if result.tool_key != CONTROL_MARK_COMPLETE:
            return result
        return self._check_or_block(result)

    def allow_completion(self) -> tuple[bool, str]:
        """Block should_continue=False when criteria are unmet (STOP-GATE-SHOULD-CONTINUE)."""
        if self._expression.is_satisfied():
            return True, ""
        return False, self._build_error_message()

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _check_or_block(self, result: ToolResult) -> ToolResult:
        if self._expression.is_satisfied():
            return result
        error = self._build_error_message()
        return ToolResult(tool_key=result.tool_key, output={"error": error})

    def _build_error_message(self) -> str:
        failing = self._expression.failing_criteria()
        lines = [
            "Completion blocked. The following success criteria are not yet met:",
            "",
        ]
        for c in failing:
            lines.append(f"  [{c.criterion_id}] {c.description}")
            lines.append(f"  Progress: {c.progress()}")
            lines.append("")
        lines.append(
            "Continue working until all criteria are satisfied, then call "
            "control.mark_complete again."
        )
        return "\n".join(lines).rstrip()
