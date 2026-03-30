"""
===============================================================================
File: harnessiq/interfaces/formalization/behaviors/pace/checkpoint.py

What this file does:
- Defines part of the abstract formalization interface surface used to describe
  harness behavior declaratively.
- Concrete progress-checkpoint cadence behavior.

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


class ProgressCheckpointBehavior(BaseExecutionPaceLayer):
    """Require periodic progress-recording tool calls."""

    def __init__(
        self,
        every_n_calls: int = 5,
        checkpoint_patterns: tuple[str, ...] = ("memory.checkpoint", "control.emit_decision"),
        blocked_until_checkpointed: tuple[str, ...] = ("*",),
    ) -> None:
        self._every_n_calls = int(every_n_calls)
        self._checkpoint_patterns = tuple(checkpoint_patterns)
        self._blocked_patterns = tuple(blocked_until_checkpointed)
        self._calls_since_checkpoint = 0
        self._checkpoint_pending = False

    def get_pace_rules(self) -> tuple[PaceRuleSpec, ...]:
        return (
            PaceRuleSpec(
                rule_id="CHECKPOINT_EVERY_N",
                description=(
                    f"After every {self._every_n_calls} tool calls, a progress-recording tool "
                    f"matching {self._checkpoint_patterns} must be called before blocked "
                    "action tools become visible again."
                ),
                trigger_every_n=self._every_n_calls,
                trigger_unit="tool_calls",
                required_action_patterns=self._checkpoint_patterns,
                blocked_until_satisfied=self._blocked_patterns,
            ),
        )

    def is_pace_rule_satisfied(self, rule: PaceRuleSpec) -> bool:
        del rule
        return not self._checkpoint_pending

    def record_pace_action(self, tool_key: str, rule: PaceRuleSpec) -> None:
        del tool_key, rule
        self._checkpoint_pending = False
        self._calls_since_checkpoint = 0

    def on_tool_result(self, result: ToolResult) -> ToolResult:
        if any(_is_tool_allowed(result.tool_key, (pattern,)) for pattern in self._checkpoint_patterns):
            self._checkpoint_pending = False
            self._calls_since_checkpoint = 0
            return super().on_tool_result(result)
        self._calls_since_checkpoint += 1
        if self._calls_since_checkpoint >= self._every_n_calls:
            self._checkpoint_pending = True
        return super().on_tool_result(result)

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        status = "pending" if self._checkpoint_pending else "satisfied"
        content = "\n".join(
            [
                f"Checkpoint status: {status}",
                f"Calls since checkpoint: {self._calls_since_checkpoint}/{self._every_n_calls}",
                f"Checkpoint patterns: {self._checkpoint_patterns}",
            ]
        )
        return (
            *super().get_parameter_sections(),
            AgentParameterSection(title=f"Behavior State: {self.layer_id}", content=content),
        )
