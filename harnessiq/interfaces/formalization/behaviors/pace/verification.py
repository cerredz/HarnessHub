"""
===============================================================================
File: harnessiq/interfaces/formalization/behaviors/pace/verification.py

What this file does:
- Defines part of the abstract formalization interface surface used to describe
  harness behavior declaratively.
- Concrete post-write verification behavior.

Use cases:
- Subclass or import these interfaces when building a new formalization layer
  family or behavior.

How to use it:
- Use the abstractions here to declare behavior, rules, and configuration in a
  form the runtime can later inspect or enforce.

Intent:
- Keep formalization contracts explicit and composable so harness rules are
  visible in code and docs.
===============================================================================
"""

from __future__ import annotations

from harnessiq.shared.agents import AgentParameterSection
from harnessiq.shared.tools import ToolResult

from .base import BaseExecutionPaceLayer, PaceRuleSpec, _is_tool_allowed


class VerificationBehavior(BaseExecutionPaceLayer):
    """Require a verification tool call after matching write operations."""

    def __init__(
        self,
        write_patterns: tuple[str, ...],
        verification_patterns: tuple[str, ...] = ("validation.*",),
        blocked_until_verified: tuple[str, ...] = ("*",),
    ) -> None:
        self._write_patterns = tuple(write_patterns)
        self._verification_patterns = tuple(verification_patterns)
        self._blocked_patterns = tuple(blocked_until_verified)
        self._verification_pending = False
        self._last_write_tool: str | None = None

    def get_pace_rules(self) -> tuple[PaceRuleSpec, ...]:
        return (
            PaceRuleSpec(
                rule_id="VERIFY_AFTER_WRITE",
                description=(
                    f"After a tool matching {self._write_patterns} is called, a verification "
                    f"tool matching {self._verification_patterns} must be called before blocked "
                    "action tools become visible again."
                ),
                trigger_every_n=1,
                trigger_unit="write_events",
                required_action_patterns=self._verification_patterns,
                blocked_until_satisfied=self._blocked_patterns,
            ),
        )

    def is_pace_rule_satisfied(self, rule: PaceRuleSpec) -> bool:
        del rule
        return not self._verification_pending

    def record_pace_action(self, tool_key: str, rule: PaceRuleSpec) -> None:
        del tool_key, rule
        self._verification_pending = False
        self._last_write_tool = None

    def on_tool_result(self, result: ToolResult) -> ToolResult:
        if any(_is_tool_allowed(result.tool_key, (pattern,)) for pattern in self._verification_patterns):
            self._verification_pending = False
            self._last_write_tool = None
            return super().on_tool_result(result)
        if any(_is_tool_allowed(result.tool_key, (pattern,)) for pattern in self._write_patterns):
            self._verification_pending = True
            self._last_write_tool = result.tool_key
        return super().on_tool_result(result)

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        status = "pending" if self._verification_pending else "satisfied"
        content = "\n".join(
            [
                f"Verification status: {status}",
                f"Write patterns: {self._write_patterns}",
                f"Verification patterns: {self._verification_patterns}",
                f"Last write tool: {self._last_write_tool or 'none'}",
            ]
        )
        return (
            *super().get_parameter_sections(),
            AgentParameterSection(title=f"Behavior State: {self.layer_id}", content=content),
        )
