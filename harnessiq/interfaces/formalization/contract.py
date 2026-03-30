"""
===============================================================================
File: harnessiq/interfaces/formalization/contract.py

What this file does:
- Defines part of the abstract formalization interface surface used to describe
  harness behavior declaratively.
- Abstract execution-contract layer for formalized harness inputs and outputs.
  Contract layers answer the most basic formalization question: what must be
  available before work begins, what must exist before the task is complete,
  and what execution budget bounds the run. The class in this module keeps
  those requirements declarative so the runtime can later validate them
  deterministically.

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

from harnessiq.shared.formalization import BudgetSpec, FieldSpec, LayerRuleRecord

from .base import BaseFormalizationLayer


class BaseContractLayer(BaseFormalizationLayer, ABC):
    """Typed base for execution-contract formalization layers.

    Subclasses declare typed input and output surfaces plus an optional budget.
    The default documentation methods convert those declarations into identity
    prose, an agent-facing contract block, and auditable rule records.
    """

    @abstractmethod
    def get_input_spec(self) -> Sequence[FieldSpec]:
        """Return the declared input fields for this contract."""

    @abstractmethod
    def get_output_spec(self) -> Sequence[FieldSpec]:
        """Return the declared output fields for this contract."""

    @abstractmethod
    def get_budget_spec(self) -> BudgetSpec | None:
        """Return the execution budget declared by this contract."""

    def get_contract_rules(self) -> Sequence[LayerRuleRecord]:
        """Return the default auditable rule set for this contract layer."""
        rules: list[LayerRuleRecord] = []
        required_inputs = [field.name for field in self.get_input_spec() if field.required]
        if required_inputs:
            rules.append(
                LayerRuleRecord(
                    rule_id="CONTRACT-INPUTS",
                    description=(
                        "Required inputs must exist before substantive work begins: "
                        + ", ".join(required_inputs)
                        + "."
                    ),
                    enforced_at="on_agent_prepare",
                    enforcement_type="raise",
                )
            )

        required_outputs = [field.name for field in self.get_output_spec() if field.required]
        if required_outputs:
            rules.append(
                LayerRuleRecord(
                    rule_id="CONTRACT-OUTPUTS",
                    description=(
                        "Required outputs must exist before the harness is considered complete: "
                        + ", ".join(required_outputs)
                        + "."
                    ),
                    enforced_at="on_tool_result",
                    enforcement_type="raise",
                )
            )

        budget = self.get_budget_spec()
        if budget is not None:
            rules.append(
                LayerRuleRecord(
                    rule_id="CONTRACT-BUDGET",
                    description=(
                        "Execution must stay within the declared budget: "
                        f"{self._format_budget(budget)}."
                    ),
                    enforced_at="on_tool_result",
                    enforcement_type="raise",
                )
            )
        return tuple(rules)

    def _describe_identity(self) -> str:
        required_inputs = [field.name for field in self.get_input_spec() if field.required]
        required_outputs = [field.name for field in self.get_output_spec() if field.required]
        return self._compose_identity(
            what=(
                "This layer defines the execution contract for a harness, including its typed "
                "inputs, required outputs, and resource budget."
            ),
            why=(
                "A harness needs explicit start and finish conditions so agent behavior does not "
                "depend on ambiguous prompt wording or hidden runtime assumptions."
            ),
            how=(
                f"Required inputs: {', '.join(required_inputs) or 'none'}. "
                f"Required outputs: {', '.join(required_outputs) or 'none'}. "
                f"Budget: {self._format_budget(self.get_budget_spec())}."
            ),
            intent=(
                "Make the work contract inspectable ahead of time and ready for deterministic "
                "validation by the runtime."
            ),
        )

    def _describe_contract(self) -> str:
        inputs = "\n".join(self._format_field(field) for field in self.get_input_spec()) or "- No input fields declared."
        outputs = "\n".join(self._format_field(field) for field in self.get_output_spec()) or "- No output fields declared."
        return (
            "This contract formalizes the data boundary for the harness.\n\n"
            "Inputs the harness expects before substantive work begins:\n"
            f"{inputs}\n\n"
            "Outputs that should exist before the task is considered complete:\n"
            f"{outputs}\n\n"
            "Execution budget enforced by the runtime:\n"
            f"- {self._format_budget(self.get_budget_spec())}"
        )

    def _describe_rules(self) -> Sequence[LayerRuleRecord]:
        return tuple(self.get_contract_rules())

    def _describe_configuration(self) -> Mapping[str, Any]:
        budget = self.get_budget_spec()
        return {
            "inputs": [asdict(field) for field in self.get_input_spec()],
            "outputs": [asdict(field) for field in self.get_output_spec()],
            "budget": None if budget is None else asdict(budget),
        }


__all__ = ["BaseContractLayer"]
