"""Shared abstractions for behavior-oriented formalization layers."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from harnessiq.shared.formalization import FormalizationHookName, LayerRuleRecord

from ..base import BaseFormalizationLayer

BehaviorEnforcementMode = Literal["prompt_only", "code_enforced", "code_and_prompt"]
BehaviorViolationAction = Literal["hide_tool", "block_result", "pause", "warn", "none"]


@dataclass(frozen=True, slots=True)
class BehaviorConstraint:
    """One declarative behavioral rule enforced by a behavior layer."""

    constraint_id: str
    description: str
    category: str
    enforcement_mode: BehaviorEnforcementMode = "code_and_prompt"
    enforced_at: FormalizationHookName = "filter_tool_keys"
    violation_action: BehaviorViolationAction = "hide_tool"


class BaseBehaviorLayer(BaseFormalizationLayer):
    """Base class for behavior formalization layers."""

    @abstractmethod
    def get_behavioral_constraints(self) -> Sequence[BehaviorConstraint]:
        """Return the behavioral constraints declared by this layer."""

    def _describe_identity(self) -> str:
        constraints = tuple(self.get_behavioral_constraints())
        categories = sorted({constraint.category for constraint in constraints})
        enforced_count = sum(
            1
            for constraint in constraints
            if constraint.enforcement_mode != "prompt_only"
        )
        return (
            f"You are operating under {len(constraints)} behavioral constraint(s) "
            f"in {len(categories)} category/ies: {', '.join(categories) or 'none'}. "
            f"{enforced_count} of these are enforced deterministically in Python code."
        )

    def _describe_contract(self) -> str:
        lines: list[str] = []
        for constraint in self.get_behavioral_constraints():
            mode_note = {
                "prompt_only": " [guidance only]",
                "code_enforced": " [enforced in Python code]",
                "code_and_prompt": " [enforced in Python code]",
            }.get(constraint.enforcement_mode, "")
            action_note = {
                "hide_tool": "Tool will be hidden when violated.",
                "block_result": "Tool result will be blocked when violated.",
                "pause": "Run will pause when violated.",
                "warn": "A warning will be appended when violated.",
                "none": "",
            }.get(constraint.violation_action, "")
            text = f"[{constraint.constraint_id}]{mode_note}: {constraint.description}"
            if action_note:
                text = f"{text} {action_note}"
            lines.append(text)
        if not lines:
            return "No behavioral constraints configured."
        return "\n".join(lines)

    def _describe_rules(self) -> Sequence[LayerRuleRecord]:
        return tuple(
            LayerRuleRecord(
                rule_id=constraint.constraint_id,
                description=constraint.description,
                enforced_at=constraint.enforced_at,
                enforcement_type=_violation_action_to_enforcement_type(constraint.violation_action),
            )
            for constraint in self.get_behavioral_constraints()
            if constraint.enforcement_mode != "prompt_only"
        )

    def _describe_configuration(self) -> Mapping[str, Any]:
        constraints = tuple(self.get_behavioral_constraints())
        return {
            "constraint_count": len(constraints),
            "constraints": [
                {
                    "id": constraint.constraint_id,
                    "category": constraint.category,
                    "enforcement_mode": constraint.enforcement_mode,
                    "enforced_at": constraint.enforced_at,
                    "violation_action": constraint.violation_action,
                    "description": constraint.description,
                }
                for constraint in constraints
            ],
        }

    def augment_system_prompt(self, system_prompt: str) -> str:
        constraints = [
            constraint
            for constraint in self.get_behavioral_constraints()
            if constraint.enforcement_mode in ("code_and_prompt", "prompt_only")
        ]
        if not constraints:
            return system_prompt
        lines = [f"{system_prompt}\n\n[BEHAVIORAL CONSTRAINTS: {self.layer_id}]"]
        lines.extend(
            f"  [{constraint.constraint_id}] {constraint.description}"
            for constraint in constraints
        )
        return "\n".join(lines)


def _violation_action_to_enforcement_type(action: BehaviorViolationAction) -> str:
    return {
        "hide_tool": "block",
        "block_result": "raise",
        "pause": "raise",
        "warn": "transform",
        "none": "allow",
    }[action]


__all__ = [
    "BaseBehaviorLayer",
    "BehaviorConstraint",
    "BehaviorEnforcementMode",
    "BehaviorViolationAction",
]
