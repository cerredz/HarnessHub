"""Concrete uncertainty-signaling behavior."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from harnessiq.shared.agents import AgentParameterSection
from harnessiq.shared.tools import ToolCall, ToolResult
from harnessiq.toolset import define_tool

from .base import BaseCommunicationBehaviorLayer, CommunicationRuleSpec, _is_tool_allowed


class UncertaintySignalingBehavior(BaseCommunicationBehaviorLayer):
    """Require explicit uncertainty signaling after empty observed results."""

    SIGNAL_TOOL_KEY = "behavior.signal_uncertainty"

    def __init__(
        self,
        *,
        monitored_patterns: tuple[str, ...],
        blocked_patterns: tuple[str, ...] = ("artifact.*", "control.mark_complete"),
    ) -> None:
        if not monitored_patterns:
            raise ValueError("monitored_patterns must not be empty.")
        self._monitored_patterns = tuple(monitored_patterns)
        self._blocked_patterns = tuple(blocked_patterns)
        self._uncertainty_due = False
        self._last_empty_tool: str | None = None
        self._signals: list[dict[str, object]] = []

    def get_communication_rules(self) -> tuple[CommunicationRuleSpec, ...]:
        return (
            CommunicationRuleSpec(
                rule_id="UNCERTAINTY_SIGNAL_REQUIRED",
                description=(
                    f"When tools matching {self._monitored_patterns} return empty results, "
                    f"call {self.SIGNAL_TOOL_KEY} before tools matching {self._blocked_patterns} continue."
                ),
                required_tool_patterns=(self.SIGNAL_TOOL_KEY,),
                trigger="after_empty_result",
                trigger_n=1,
                blocks_patterns=self._blocked_patterns,
            ),
        )

    def is_communication_due(self, rule: CommunicationRuleSpec) -> bool:
        del rule
        return self._uncertainty_due

    def record_communication(self, tool_key: str, rule: CommunicationRuleSpec) -> None:
        del tool_key, rule
        self._uncertainty_due = False

    def on_tool_result_event(self, tool_call: ToolCall, result: ToolResult) -> ToolResult:
        if _is_tool_allowed(tool_call.tool_key, self._monitored_patterns) and _is_empty_output(result.output):
            self._uncertainty_due = True
            self._last_empty_tool = tool_call.tool_key
        return super().on_tool_result(result)

    def get_formalization_tools(self):
        return (
            define_tool(
                key=self.SIGNAL_TOOL_KEY,
                description="Record that the agent is uncertain after observing empty or inconclusive results.",
                parameters={
                    "reason": {"type": "string", "description": "Why the agent is uncertain."},
                    "observed_tool": {
                        "type": "string",
                        "description": "Tool that produced the empty or inconclusive result.",
                    },
                    "next_step": {
                        "type": "string",
                        "description": "The recovery or follow-up step the agent will take.",
                    },
                },
                required=["reason", "observed_tool"],
                handler=self._handle_uncertainty_signal,
            ),
        )

    def _handle_uncertainty_signal(self, arguments: dict[str, object]) -> dict[str, object]:
        payload = {
            "reason": str(arguments["reason"]),
            "observed_tool": str(arguments["observed_tool"]),
            "next_step": str(arguments.get("next_step", "")),
        }
        self._signals.append(payload)
        return payload

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        lines = [
            f"Uncertainty due: {'yes' if self._uncertainty_due else 'no'}",
            f"Monitored patterns: {self._monitored_patterns}",
            f"Blocked patterns: {self._blocked_patterns}",
            f"Last empty-result tool: {self._last_empty_tool or 'none'}",
            f"Signals recorded: {len(self._signals)}",
        ]
        return (
            *super().get_parameter_sections(),
            AgentParameterSection(title=f"Behavior State: {self.layer_id}", content="\n".join(lines)),
        )


def _is_empty_output(output: Any) -> bool:
    if output is None:
        return True
    if isinstance(output, str):
        return not output.strip()
    if isinstance(output, Sequence) and not isinstance(output, (str, bytes, bytearray)):
        return len(output) == 0
    if isinstance(output, dict):
        if not output:
            return True
        if "results" in output and isinstance(output["results"], list):
            return len(output["results"]) == 0
        if "items" in output and isinstance(output["items"], list):
            return len(output["items"]) == 0
    return False


__all__ = ["UncertaintySignalingBehavior"]
