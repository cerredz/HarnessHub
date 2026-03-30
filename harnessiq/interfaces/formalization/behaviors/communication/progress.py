"""Concrete progress-reporting behavior."""

from __future__ import annotations

from harnessiq.shared.agents import AgentParameterSection
from harnessiq.shared.tools import ToolResult
from harnessiq.toolset import define_tool

from .base import BaseCommunicationBehaviorLayer, CommunicationRuleSpec


class ProgressReportingBehavior(BaseCommunicationBehaviorLayer):
    """Require structured progress reports every N observed cycles or resets."""

    REPORT_TOOL_KEY = "behavior.report_progress"

    def __init__(
        self,
        *,
        every_n_cycles: int | None = None,
        every_n_resets: int | None = None,
        blocked_patterns: tuple[str, ...] = ("artifact.*", "control.mark_complete"),
    ) -> None:
        if every_n_cycles is None and every_n_resets is None:
            raise ValueError("At least one of every_n_cycles or every_n_resets must be set.")
        if every_n_cycles is not None and every_n_cycles <= 0:
            raise ValueError("every_n_cycles must be greater than zero when provided.")
        if every_n_resets is not None and every_n_resets <= 0:
            raise ValueError("every_n_resets must be greater than zero when provided.")
        self._every_n_cycles = every_n_cycles
        self._every_n_resets = every_n_resets
        self._blocked_patterns = tuple(blocked_patterns)
        self._cycles_since_report = 0
        self._resets_since_report = 0
        self._reports: list[dict[str, object]] = []

    def get_communication_rules(self) -> tuple[CommunicationRuleSpec, ...]:
        rules: list[CommunicationRuleSpec] = []
        if self._every_n_cycles is not None:
            rules.append(
                CommunicationRuleSpec(
                    rule_id="PROGRESS_REPORT_CYCLES",
                    description=(
                        f"After every {self._every_n_cycles} observed cycle(s), "
                        f"call {self.REPORT_TOOL_KEY} before tools matching {self._blocked_patterns} continue."
                    ),
                    required_tool_patterns=(self.REPORT_TOOL_KEY,),
                    trigger="every_n_cycles",
                    trigger_n=self._every_n_cycles,
                    blocks_patterns=self._blocked_patterns,
                )
            )
        if self._every_n_resets is not None:
            rules.append(
                CommunicationRuleSpec(
                    rule_id="PROGRESS_REPORT_RESETS",
                    description=(
                        f"After every {self._every_n_resets} reset(s), "
                        f"call {self.REPORT_TOOL_KEY} before tools matching {self._blocked_patterns} continue."
                    ),
                    required_tool_patterns=(self.REPORT_TOOL_KEY,),
                    trigger="every_n_resets",
                    trigger_n=self._every_n_resets,
                    blocks_patterns=self._blocked_patterns,
                )
            )
        return tuple(rules)

    def is_communication_due(self, rule: CommunicationRuleSpec) -> bool:
        if rule.trigger == "every_n_cycles":
            return self._cycles_since_report >= rule.trigger_n
        if rule.trigger == "every_n_resets":
            return self._resets_since_report >= rule.trigger_n
        return False

    def record_communication(self, tool_key: str, rule: CommunicationRuleSpec) -> None:
        del tool_key, rule
        self._cycles_since_report = 0
        self._resets_since_report = 0

    def on_tool_result(self, result: ToolResult) -> ToolResult:
        if result.tool_key != self.REPORT_TOOL_KEY:
            self._cycles_since_report += 1
        return super().on_tool_result(result)

    def on_post_reset(self) -> None:
        self._resets_since_report += 1

    def get_formalization_tools(self):
        return (
            define_tool(
                key=self.REPORT_TOOL_KEY,
                description="Record a structured progress report for the current run.",
                parameters={
                    "summary": {"type": "string", "description": "Short progress summary."},
                    "completed_steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Completed steps so far.",
                    },
                    "next_steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "What should happen next.",
                    },
                    "blockers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Current blockers, if any.",
                    },
                },
                required=["summary"],
                handler=self._handle_progress_report,
            ),
        )

    def _handle_progress_report(self, arguments: dict[str, object]) -> dict[str, object]:
        payload = {
            "summary": str(arguments["summary"]),
            "completed_steps": list(arguments.get("completed_steps", [])),
            "next_steps": list(arguments.get("next_steps", [])),
            "blockers": list(arguments.get("blockers", [])),
        }
        self._reports.append(payload)
        return payload

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        lines = [
            f"Report tool: {self.REPORT_TOOL_KEY}",
            f"Cycles since report: {self._cycles_since_report}",
            f"Resets since report: {self._resets_since_report}",
            f"Reports recorded: {len(self._reports)}",
        ]
        return (
            *super().get_parameter_sections(),
            AgentParameterSection(title=f"Behavior State: {self.layer_id}", content="\n".join(lines)),
        )


__all__ = ["ProgressReportingBehavior"]
