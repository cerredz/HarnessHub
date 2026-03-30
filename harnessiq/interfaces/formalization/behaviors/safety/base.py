"""
===============================================================================
File: harnessiq/interfaces/formalization/behaviors/safety/base.py

What this file does:
- Defines part of the abstract formalization interface surface used to describe
  harness behavior declaratively.
- Typed base classes for safety behavior layers.

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

from abc import abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from harnessiq.shared.tools import ToolCall, ToolResult

from ..base import BaseBehaviorLayer, BehaviorConstraint


@dataclass(frozen=True, slots=True)
class GuardrailSpec:
    """Declare one safety guardrail."""

    guardrail_id: str
    description: str
    protected_patterns: tuple[str, ...]
    confirmation_tool_key: str = ""
    rate_limit_n: int | None = None
    argument_block_patterns: tuple[tuple[str, str], ...] = ()


class BaseSafetyBehaviorLayer(BaseBehaviorLayer):
    """Base class for layers that guard dangerous tool usage."""

    @abstractmethod
    def get_guardrails(self) -> Sequence[GuardrailSpec]:
        """Return all safety guardrails declared by the layer."""

    @abstractmethod
    def is_guardrail_satisfied(self, guardrail: GuardrailSpec, tool_key: str) -> bool:
        """Return whether one visible tool key satisfies the guardrail."""

    def evaluate_guardrail_call(
        self,
        guardrail: GuardrailSpec,
        tool_call: ToolCall,
    ) -> tuple[bool, str]:
        for argument_key, forbidden_value in guardrail.argument_block_patterns:
            for candidate in _extract_argument_values(tool_call.arguments, argument_key):
                if forbidden_value.lower() in str(candidate).lower():
                    return (
                        False,
                        (
                            f"{tool_call.tool_key} is blocked because argument '{argument_key}' "
                            f"matches forbidden scope value '{forbidden_value}'."
                        ),
                    )
        return True, ""

    def get_behavioral_constraints(self) -> Sequence[BehaviorConstraint]:
        return tuple(
            BehaviorConstraint(
                constraint_id=guardrail.guardrail_id,
                description=guardrail.description,
                category="safety_behavior",
                enforcement_mode="code_and_prompt",
                enforced_at=(
                    "on_tool_call"
                    if guardrail.argument_block_patterns
                    else "filter_tool_keys"
                ),
                violation_action=(
                    "block_result"
                    if guardrail.argument_block_patterns
                    else "hide_tool"
                ),
            )
            for guardrail in self.get_guardrails()
        )

    def filter_tool_keys(self, tool_keys: Sequence[str]) -> tuple[str, ...]:
        permitted: list[str] = []
        for tool_key in tool_keys:
            blocked = False
            for guardrail in self.get_guardrails():
                if not any(
                    _is_tool_allowed(tool_key, (pattern,))
                    for pattern in guardrail.protected_patterns
                ):
                    continue
                if not self.is_guardrail_satisfied(guardrail, tool_key):
                    blocked = True
                    break
            if not blocked:
                permitted.append(tool_key)
        return tuple(permitted)

    def on_tool_call(self, tool_call: ToolCall) -> ToolCall | ToolResult:
        for guardrail in self.get_guardrails():
            if not any(
                _is_tool_allowed(tool_call.tool_key, (pattern,))
                for pattern in guardrail.protected_patterns
            ):
                continue
            if not self.is_guardrail_satisfied(guardrail, tool_call.tool_key):
                return ToolResult(
                    tool_key=tool_call.tool_key,
                    output={
                        "error": f"{tool_call.tool_key} is blocked until safety guardrail '{guardrail.guardrail_id}' is satisfied.",
                        "guardrail": guardrail.guardrail_id,
                    },
                )
            allowed, reason = self.evaluate_guardrail_call(guardrail, tool_call)
            if not allowed:
                return ToolResult(
                    tool_key=tool_call.tool_key,
                    output={"error": reason, "guardrail": guardrail.guardrail_id},
                )
        return tool_call


def _is_tool_allowed(tool_key: str, patterns: tuple[str, ...]) -> bool:
    from harnessiq.tools.hooks.defaults import is_tool_allowed

    return is_tool_allowed(tool_key, patterns)


def _extract_argument_values(arguments: dict[str, object], dotted_key: str) -> list[object]:
    parts = tuple(part for part in dotted_key.split(".") if part)
    if not parts:
        return []
    values: list[object] = [arguments]
    for part in parts:
        next_values: list[object] = []
        for value in values:
            if isinstance(value, dict) and part in value:
                next_values.append(value[part])
                continue
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and part in item:
                        next_values.append(item[part])
        values = next_values
        if not values:
            return []
    flattened: list[object] = []
    for value in values:
        if isinstance(value, list):
            flattened.extend(value)
        else:
            flattened.append(value)
    return flattened


__all__ = [
    "BaseSafetyBehaviorLayer",
    "GuardrailSpec",
]
