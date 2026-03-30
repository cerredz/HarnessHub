"""
===============================================================================
File: harnessiq/interfaces/formalization/artifact.py

What this file does:
- Defines part of the abstract formalization interface surface used to describe
  harness behavior declaratively.
- Abstract artifact-production layer for formalized output materialization.
  Artifact layers let a harness declare which durable files or structured
  outputs matter as first-class deliverables. The interface is intentionally
  narrow: subclasses only declare artifact specs, while the base class turns
  those specs into default self-documentation and auditable rules.

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

from harnessiq.shared.formalization import ArtifactSpec, LayerRuleRecord

from .base import BaseFormalizationLayer


class BaseArtifactLayer(BaseFormalizationLayer, ABC):
    """Typed base for artifact-production formalization layers."""

    @abstractmethod
    def get_artifact_specs(self) -> Sequence[ArtifactSpec]:
        """Return the declared artifacts tracked by this layer."""

    def get_artifact_rules(self) -> Sequence[LayerRuleRecord]:
        """Return the default rule set for this artifact layer."""
        required_artifacts = [
            spec.name for spec in self.get_artifact_specs() if spec.required_before_complete
        ]
        rules: list[LayerRuleRecord] = []
        if required_artifacts:
            rules.append(
                LayerRuleRecord(
                    rule_id="ARTIFACT-REQUIRED",
                    description=(
                        "The following artifacts must be produced before completion: "
                        + ", ".join(required_artifacts)
                        + "."
                    ),
                    enforced_at="on_tool_result",
                    enforcement_type="raise",
                )
            )
        return tuple(rules)

    def _describe_identity(self) -> str:
        specs = tuple(self.get_artifact_specs())
        required = [spec.name for spec in specs if spec.required_before_complete]
        return self._compose_identity(
            what=(
                "This layer formalizes the artifact surface for a harness by declaring which "
                "named outputs should exist and what shape they take."
            ),
            why=(
                "Artifact production is often the real deliverable of an agent run, so it needs "
                "to be modeled explicitly instead of inferred after the fact."
            ),
            how=(
                f"The layer tracks {len(specs)} artifact declaration(s). "
                f"Required before completion: {', '.join(required) or 'none'}."
            ),
            intent=(
                "Make output materialization inspectable, enforceable, and easy to surface in "
                "both runtime context and developer review."
            ),
        )

    def _describe_contract(self) -> str:
        specs = "\n".join(
            (
                f"- {spec.name} ({spec.artifact_type}): {self._ensure_sentence(spec.description)}"
                + (" Required before completion." if spec.required_before_complete else "")
                + (f" Produced by `{spec.produced_by_tool}`." if spec.produced_by_tool else "")
            )
            for spec in self.get_artifact_specs()
        ) or "- No artifacts declared."
        return (
            "This layer describes the durable outputs the harness is expected to materialize.\n\n"
            "Declared artifacts:\n"
            f"{specs}"
        )

    def _describe_rules(self) -> Sequence[LayerRuleRecord]:
        return tuple(self.get_artifact_rules())

    def _describe_configuration(self) -> Mapping[str, Any]:
        return {"artifacts": [asdict(spec) for spec in self.get_artifact_specs()]}


__all__ = ["BaseArtifactLayer"]
