"""
===============================================================================
File: harnessiq/formalization/roles/layer.py

What this file does:
- Implements RoleLayer, a formalization layer that injects persona descriptions
  into the system prompt at declared positions.
- Purely semantic — no tool interaction, no filter_tool_keys logic, no
  on_tool_result logic.

Use cases:
- Pass RoleLayer instances via BaseAgent(formalization_layers=[...]) or use the
  roles= sugar on BaseAgent to have the layer created automatically.

How to use it:
- Construct with one or more RoleSpec instances. Each spec is injected at its
  declared position when augment_system_prompt is called.

Intent:
- Give agents an explicit, inspectable, auditable identity that appears in
  describe() output and in the context window parameter sections.
===============================================================================
"""

from __future__ import annotations

import warnings
from collections.abc import Sequence
from typing import Any

from harnessiq.formalization.base import BaseFormalizationLayer
from harnessiq.shared.agents import AgentParameterSection
from harnessiq.shared.formalization import LayerRuleRecord

from .spec import RoleSpec


class RoleLayer(BaseFormalizationLayer):
    """Injects role (persona) descriptions into the system prompt.

    Purely semantic — no tool interaction. Created automatically by BaseAgent
    when roles= is provided, or constructed directly for explicit control.
    """

    def __init__(self, roles: Sequence[RoleSpec]) -> None:
        if not roles:
            raise ValueError("RoleLayer requires at least one RoleSpec.")
        self._roles = tuple(roles)

    @property
    def layer_id(self) -> str:
        return "RoleLayer"

    # ── Documentation ──────────────────────────────────────────────────────────

    def _describe_identity(self) -> str:
        names = ", ".join(r.name for r in self._roles)
        return (
            f"You are operating under {len(self._roles)} declared role(s): {names}. "
            f"These define your identity and operating persona for this run."
        )

    def _describe_contract(self) -> str:
        lines = ["Act consistently with the role(s) declared below:", ""]
        for role in self._roles:
            lines.append(f"[{role.name}] (injected at: {role.position})")
            lines.append(role.description)
            lines.append("")
        return "\n".join(lines).rstrip()

    def _describe_rules(self) -> tuple[LayerRuleRecord, ...]:
        return tuple(
            LayerRuleRecord(
                rule_id=f"ROLE-INJECT-{role.name.upper().replace(' ', '-')}",
                description=(
                    f"'{role.name}' role description is injected into the system "
                    f"prompt at position='{role.position}' via augment_system_prompt."
                ),
                enforced_at="augment_system_prompt",
                enforcement_type="inject",
            )
            for role in self._roles
        )

    def _describe_configuration(self) -> dict[str, Any]:
        return {
            "role_count": len(self._roles),
            "roles": [
                {
                    "name": r.name,
                    "position": r.position,
                    "marker_text": r.marker_text,
                    "show_in_parameter_sections": r.show_in_parameter_sections,
                }
                for r in self._roles
            ],
        }

    # ── System prompt injection ────────────────────────────────────────────────

    def augment_system_prompt(self, prompt: str) -> str:
        """Inject all roles at their declared positions."""
        result = prompt
        for role in self._roles:
            block = f"[ROLE: {role.name}]\n{role.description}"
            if role.position == "top":
                result = block + "\n\n" + result
            elif role.position == "bottom":
                result = result + "\n\n" + block
            elif role.position == "after_marker":
                if role.marker_text in result:
                    idx = result.index(role.marker_text) + len(role.marker_text)
                    result = result[:idx] + "\n\n" + block + result[idx:]
                else:
                    warnings.warn(
                        f"RoleSpec '{role.name}': marker_text '{role.marker_text}' "
                        f"not found in assembled prompt. Falling back to 'bottom'.",
                        stacklevel=2,
                    )
                    result = result + "\n\n" + block
        return result

    # ── Context window sections ────────────────────────────────────────────────

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        """Return one parameter section per visible role, plus the standard layer section."""
        base = super().get_parameter_sections()
        visible = [r for r in self._roles if r.show_in_parameter_sections]
        if not visible:
            return base
        role_sections = tuple(
            AgentParameterSection(
                title=f"Role: {role.name}",
                content=role.description,
            )
            for role in visible
        )
        return base + role_sections
