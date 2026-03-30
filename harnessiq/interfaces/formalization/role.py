"""
===============================================================================
File: harnessiq/interfaces/formalization/role.py

What this file does:
- Defines part of the abstract formalization interface surface used to describe
  harness behavior declaratively.
- Abstract role-selection layer for multi-role harness formalization. Role
  layers formalize agent identity switching without forcing that logic into the
  harness itself. A role can inject prompt fragments and narrow the visible
  tool surface, while the harness stays responsible for deciding which role is
  currently active.

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

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from typing import Any

from harnessiq.shared.formalization import LayerRuleRecord, RoleSpec

from .base import BaseFormalizationLayer


class BaseRoleLayer(BaseFormalizationLayer, ABC):
    """Typed base for multi-role formalization layers."""

    @abstractmethod
    def get_roles(self) -> Sequence[RoleSpec]:
        """Return the available roles for this layer."""

    @abstractmethod
    def get_active_role_index(self) -> int:
        """Return the zero-based active role index."""

    @property
    def active_role(self) -> RoleSpec:
        """Return the currently active role."""
        roles = tuple(self.get_roles())
        return roles[self.get_active_role_index()]

    def augment_system_prompt(self, system_prompt: str) -> str:
        fragment = self.active_role.system_prompt_fragment.strip()
        if not fragment:
            return system_prompt
        return f"{system_prompt}\n\n{fragment}"

    def filter_tool_keys(self, tool_keys: Sequence[str]) -> tuple[str, ...]:
        return self._filter_with_patterns(tool_keys, self.active_role.allowed_tool_patterns)

    def _describe_identity(self) -> str:
        roles = tuple(self.get_roles())
        return self._compose_identity(
            what=(
                "This layer formalizes a set of named agent roles that can change prompt framing "
                "and tool visibility without changing the underlying harness."
            ),
            why=(
                "Role switching is easier to reason about when the available roles and their "
                "runtime consequences are explicit and reviewable."
            ),
            how=(
                f"Declared roles: {', '.join(role.name for role in roles) or 'none'}. "
                f"Active role: {self.active_role.name!r}."
            ),
            intent=(
                "Let a harness adopt different operating postures through a documented, typed "
                "interface instead of ad hoc prompt rewrites."
            ),
        )

    def _describe_contract(self) -> str:
        lines = "\n".join(
            f"- {role.name}: {self._ensure_sentence(role.description)}"
            for role in self.get_roles()
        ) or "- No roles declared."
        return (
            "This layer defines the role catalog available to the harness.\n\n"
            "Roles:\n"
            f"{lines}"
        )

    def _describe_rules(self) -> Sequence[LayerRuleRecord]:
        return (
            LayerRuleRecord(
                rule_id="ROLE-TOOL-FILTER",
                description="The active role narrows the visible tool surface to its allowed tool patterns.",
                enforced_at="filter_tool_keys",
                enforcement_type="block",
            ),
        )

    def _describe_configuration(self) -> Mapping[str, Any]:
        return {
            "active_role_index": self.get_active_role_index(),
            "roles": [asdict(role) for role in self.get_roles()],
        }


__all__ = ["BaseRoleLayer"]
