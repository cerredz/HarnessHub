"""Concrete irreversible-action gate behavior."""

from __future__ import annotations

from harnessiq.shared.agents import AgentParameterSection
from harnessiq.shared.tools import ToolCall, ToolResult
from harnessiq.toolset import define_tool

from .base import BaseSafetyBehaviorLayer, GuardrailSpec, _is_tool_allowed


class IrreversibleActionGateBehavior(BaseSafetyBehaviorLayer):
    """Require explicit confirmation before protected tools become visible."""

    CONFIRM_TOOL_KEY = "behavior.confirm_action"

    def __init__(self, *, irreversible_patterns: tuple[str, ...]) -> None:
        self._irreversible_patterns = tuple(irreversible_patterns)
        self._confirmed: dict[str, str] = {}

    def get_guardrails(self) -> tuple[GuardrailSpec, ...]:
        return (
            GuardrailSpec(
                guardrail_id="IRREVERSIBLE_ACTION_GATE",
                description=(
                    f"Tools matching {self._irreversible_patterns} require explicit confirmation via "
                    "behavior.confirm_action before one confirmed call becomes visible."
                ),
                protected_patterns=self._irreversible_patterns,
                confirmation_tool_key=self.CONFIRM_TOOL_KEY,
            ),
        )

    def is_guardrail_satisfied(self, guardrail: GuardrailSpec, tool_key: str) -> bool:
        del guardrail
        return tool_key in self._confirmed

    def get_formalization_tools(self):
        return (
            define_tool(
                key=self.CONFIRM_TOOL_KEY,
                description=(
                    "Confirm intent to call one irreversible tool. "
                    "This unlocks the exact target tool for one call."
                ),
                parameters={
                    "target_tool": {
                        "type": "string",
                        "description": "Exact tool key that should be unlocked.",
                    },
                    "rationale": {
                        "type": "string",
                        "description": "Why this irreversible action is necessary.",
                    },
                },
                required=["target_tool", "rationale"],
                handler=self._handle_confirm,
            ),
        )

    def _handle_confirm(self, arguments: dict[str, object]) -> dict[str, object]:
        target_tool = str(arguments["target_tool"])
        rationale = str(arguments["rationale"])
        self._confirmed[target_tool] = rationale
        return {"confirmed": True, "target_tool": target_tool, "rationale": rationale}

    def on_tool_result_event(self, tool_call: ToolCall, result: ToolResult) -> ToolResult:
        if any(
            _is_tool_allowed(tool_call.tool_key, (pattern,))
            for pattern in self._irreversible_patterns
        ):
            self._confirmed.pop(tool_call.tool_key, None)
        return result

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        lines = [
            f"Protected patterns: {self._irreversible_patterns}",
            f"Confirmation tool: {self.CONFIRM_TOOL_KEY}",
            f"Confirmed tools awaiting execution: {sorted(self._confirmed) or 'none'}",
        ]
        return (
            *super().get_parameter_sections(),
            AgentParameterSection(title=f"Behavior State: {self.layer_id}", content="\n".join(lines)),
        )


__all__ = ["IrreversibleActionGateBehavior"]
