"""
===============================================================================
File: harnessiq/interfaces/formalization/hook_layer.py

What this file does:
- Defines part of the abstract formalization interface surface used to describe
  harness behavior declaratively.
- Abstract hook-behavior layer for stateful runtime interception. The existing
  runtime already has hook concepts, but a formalization hook layer captures a
  different concern: behaviors that belong to a self-documenting formalization
  object and may carry their own state or rule declarations.

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

from harnessiq.shared.formalization import HookBehaviorSpec, LayerRuleRecord

from .base import BaseFormalizationLayer


class BaseHookLayer(BaseFormalizationLayer, ABC):
    """Typed base for hook-oriented formalization layers."""

    @abstractmethod
    def get_hook_behaviors(self) -> Sequence[HookBehaviorSpec]:
        """Return the hook behaviors owned by this layer."""

    def get_hook_rules(self) -> Sequence[LayerRuleRecord]:
        """Return the default rule set derived from the declared hook behaviors."""
        return tuple(
            LayerRuleRecord(
                rule_id=f"HOOK-{behavior.lifecycle_hook.upper()}-{behavior.name.upper().replace(' ', '-')}",
                description=behavior.description,
                enforced_at=behavior.lifecycle_hook,
                enforcement_type="transform" if behavior.mutates_context else "allow",
            )
            for behavior in self.get_hook_behaviors()
        )

    def _describe_identity(self) -> str:
        hooks = tuple(self.get_hook_behaviors())
        phases = sorted({hook.lifecycle_hook for hook in hooks})
        return self._compose_identity(
            what=(
                "This layer formalizes hook-owned runtime behavior that should participate in "
                "specific harness lifecycle phases."
            ),
            why=(
                "Some runtime interventions are not just free-floating hooks; they are part of a "
                "layer's contract and should be documented alongside the layer that owns them."
            ),
            how=(
                f"The layer declares {len(hooks)} hook behavior(s) across "
                f"{', '.join(phases) or 'no hooks'}."
            ),
            intent=(
                "Keep lifecycle interventions inspectable and attributable to the formalization "
                "layer that defines them."
            ),
        )

    def _describe_contract(self) -> str:
        behaviors = "\n".join(
            f"- {behavior.name} ({behavior.lifecycle_hook}): {self._ensure_sentence(behavior.description)}"
            for behavior in self.get_hook_behaviors()
        ) or "- No hook behaviors declared."
        return (
            "This layer owns lifecycle-specific behaviors that the harness may call at runtime.\n\n"
            "Declared hook behaviors:\n"
            f"{behaviors}"
        )

    def _describe_rules(self) -> Sequence[LayerRuleRecord]:
        return tuple(self.get_hook_rules())

    def _describe_configuration(self) -> Mapping[str, Any]:
        return {
            "hook_behaviors": [asdict(behavior) for behavior in self.get_hook_behaviors()],
        }


__all__ = ["BaseHookLayer"]
