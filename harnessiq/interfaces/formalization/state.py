"""Abstract durable-state layer for formalized reset continuity.

State layers define typed fields that survive resets and restarts. The point is
not only persistence. The state schema also explains to the harness and the
agent which values matter across context boundaries and how they are allowed to
change over time.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from typing import Any

from harnessiq.shared.agents import AgentParameterSection, json_parameter_section
from harnessiq.shared.formalization import LayerRuleRecord, StateFieldSpec

from .base import BaseFormalizationLayer


class BaseStateLayer(BaseFormalizationLayer, ABC):
    """Typed base for durable state formalization layers."""

    @abstractmethod
    def get_state_fields(self) -> Sequence[StateFieldSpec]:
        """Return the typed state schema for this layer."""

    @abstractmethod
    def get_state_snapshot(self) -> Mapping[str, Any]:
        """Return the current durable state snapshot."""

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        return (
            *super().get_parameter_sections(),
            json_parameter_section("Formalization State", self.get_state_snapshot()),
        )

    def _describe_identity(self) -> str:
        fields = tuple(self.get_state_fields())
        pointer_names = [field.name for field in fields if field.is_continuation_pointer]
        return self._compose_identity(
            what=(
                "This layer formalizes durable harness state by declaring typed fields whose "
                "values survive context resets and resumptions."
            ),
            why=(
                "Reset continuity is safer when the persisted fields and their update semantics "
                "are explicit instead of being hidden in ad hoc storage logic."
            ),
            how=(
                f"The layer manages {len(fields)} typed field(s). "
                f"Continuation pointer: {', '.join(pointer_names) or 'none'}."
            ),
            intent=(
                "Make reset continuity, resumption semantics, and write rules inspectable for "
                "both developers and the agent."
            ),
        )

    def _describe_contract(self) -> str:
        lines = "\n".join(
            (
                f"- {field.name} ({field.field_type}, {field.update_rule}): {self._ensure_sentence(field.description)}"
                + (" [CONTINUATION POINTER]" if field.is_continuation_pointer else "")
            )
            for field in self.get_state_fields()
        ) or "- No state fields declared."
        return (
            "This layer defines the durable state schema that spans resets.\n\n"
            "State fields:\n"
            f"{lines}"
        )

    def _describe_rules(self) -> Sequence[LayerRuleRecord]:
        rules: list[LayerRuleRecord] = [
            LayerRuleRecord(
                rule_id="STATE-PERSIST-PRE-RESET",
                description="State should be durably persisted before the context resets.",
                enforced_at="on_pre_reset",
                enforcement_type="persist",
            ),
            LayerRuleRecord(
                rule_id="STATE-RELOAD-POST-RESET",
                description="State should be reloaded after the context resets so the next context window is synchronized.",
                enforced_at="on_post_reset",
                enforcement_type="inject",
            ),
        ]
        for field in self.get_state_fields():
            if field.update_rule != "write_once":
                continue
            rules.append(
                LayerRuleRecord(
                    rule_id=f"STATE-WRITE-ONCE-{field.name.upper().replace('-', '_')}",
                    description=f"`{field.name}` is write-once after its first durable assignment.",
                    enforced_at="on_pre_reset",
                    enforcement_type="skip",
                )
            )
        return tuple(rules)

    def _describe_configuration(self) -> Mapping[str, Any]:
        return {
            "fields": [asdict(field) for field in self.get_state_fields()],
            "snapshot": dict(self.get_state_snapshot()),
        }


__all__ = ["BaseStateLayer"]
