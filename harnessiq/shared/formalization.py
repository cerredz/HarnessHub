"""Shared formalization records used by the public interface layer package.

This module intentionally holds the durable, dependency-light data structures
that describe a formalization layer. The interface package builds abstract
behavior on top of these records, but the records themselves live in
``harnessiq.shared`` so they can be reused by runtime code, tests, generators,
and SDK consumers without importing the higher-level interface package.

The separation matters for two reasons:

1. These records are the stable vocabulary for formalization layers. They are
   not specific to any one abstract base class.
2. The formalization interfaces are expected to be injectable into different
   harness compositions. Keeping the records in ``shared`` lets both the
   interface layer and the eventual runtime implementation depend on the same
   source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from harnessiq.shared.agents import (
    AgentContextMemoryUpdateRule,
    render_json_parameter_content,
)

FormalizationHookName = Literal[
    "augment_system_prompt",
    "filter_tool_keys",
    "get_parameter_sections",
    "on_agent_prepare",
    "on_post_reset",
    "on_pre_reset",
    "on_tool_result",
]
"""Stable hook names where a formalization layer can participate in the runtime."""

FormalizationEnforcementType = Literal[
    "advance",
    "allow",
    "block",
    "inject",
    "persist",
    "raise",
    "skip",
    "transform",
]
"""Stable vocabulary describing how a rule is enforced in deterministic code."""

StateUpdateRule = AgentContextMemoryUpdateRule
"""Alias exported with the formalization surface for state-field update semantics."""


@dataclass(frozen=True, slots=True)
class LayerRuleRecord:
    """One auditable rule declared by a formalization layer.

    The goal of this record is not just configuration. It is the bridge between
    self-documentation and deterministic enforcement:

    - ``rule_id`` gives the rule a stable reference for docs, tests, and review.
    - ``description`` explains the intended runtime behavior in prose.
    - ``enforced_at`` names the lifecycle hook where the harness should apply it.
    - ``enforcement_type`` clarifies whether the harness blocks, transforms,
      persists, raises, or otherwise constrains behavior.
    """

    rule_id: str
    description: str
    enforced_at: FormalizationHookName
    enforcement_type: FormalizationEnforcementType


@dataclass(frozen=True, slots=True)
class FormalizationDescription:
    """Structured self-description for one formalization layer.

    ``describe()`` on the interface layer returns this object so the same
    content can be rendered for two audiences:

    - developers and reviewers inspecting the harness structure
    - the model runtime, where the layer's rules need to appear in context
    """

    layer_id: str
    identity: str
    contract: str
    rules: tuple[LayerRuleRecord, ...]
    configuration: dict[str, Any]

    def render(self) -> str:
        """Render a developer-facing description block."""
        rules_block = "\n".join(
            f"  {rule.rule_id}  enforced_at={rule.enforced_at}  type={rule.enforcement_type}\n"
            f"    {rule.description}"
            for rule in self.rules
        ) or "  (none)"
        return (
            f"[{self.layer_id}]\n\n"
            f"IDENTITY\n{self.identity}\n\n"
            f"CONTRACT\n{self.contract}\n\n"
            f"RULES\n{rules_block}\n\n"
            f"CONFIGURATION\n{render_json_parameter_content(self.configuration)}"
        ).rstrip()

    def render_for_agent(self) -> str:
        """Render the agent-facing block that should be injected into context."""
        rules_block = "\n".join(
            f"- [{rule.rule_id}] {rule.description}"
            for rule in self.rules
        ) or "- No explicit rules declared."
        return (
            f"[LAYER: {self.layer_id}]\n"
            f"{self.identity}\n\n"
            "Behavioral contract:\n"
            f"{self.contract}\n\n"
            "Enforced rules (deterministic Python behavior):\n"
            f"{rules_block}"
        ).rstrip()


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """Describe one typed input or output field owned by a contract layer."""

    name: str
    field_type: str
    description: str
    required: bool = False
    default: Any = None


@dataclass(frozen=True, slots=True)
class BudgetSpec:
    """Describe the execution budget associated with a contract layer."""

    max_tokens: int | None = None
    max_resets: int | None = None
    max_wall_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class ArtifactSpec:
    """Describe one declared artifact for an artifact-oriented layer."""

    name: str
    artifact_type: str
    description: str
    required_before_complete: bool = False
    produced_by_tool: str | None = None


@dataclass(frozen=True, slots=True)
class HookBehaviorSpec:
    """Describe one hook-driven behavior owned by a hook layer."""

    name: str
    description: str
    lifecycle_hook: FormalizationHookName
    mutates_context: bool = False


@dataclass(frozen=True, slots=True)
class StageSpec:
    """Describe one deterministic execution stage in a staged harness."""

    name: str
    description: str
    system_prompt_fragment: str = ""
    allowed_tool_patterns: tuple[str, ...] = ()
    required_output_keys: tuple[str, ...] = ()
    completion_hint: str | None = None


@dataclass(frozen=True, slots=True)
class RoleSpec:
    """Describe one role that can shape prompt context and visible tools."""

    name: str
    description: str
    system_prompt_fragment: str = ""
    allowed_tool_patterns: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StateFieldSpec:
    """Describe one durable state field managed by a state layer."""

    name: str
    field_type: str
    description: str
    update_rule: StateUpdateRule = "overwrite"
    default: Any = None
    is_continuation_pointer: bool = False


__all__ = [
    "ArtifactSpec",
    "BudgetSpec",
    "FieldSpec",
    "FormalizationDescription",
    "FormalizationEnforcementType",
    "FormalizationHookName",
    "HookBehaviorSpec",
    "LayerRuleRecord",
    "RoleSpec",
    "StageSpec",
    "StateFieldSpec",
    "StateUpdateRule",
]
