"""Abstract tool-contribution layer for formalization-owned tool surfaces.

Some formalization layers do not just document behavior; they also contribute
tools that should become part of the harness runtime surface. This interface
keeps that responsibility explicit and self-documenting.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import Any

from harnessiq.shared.formalization import LayerRuleRecord
from harnessiq.shared.tools import ToolDefinition

from .base import BaseFormalizationLayer


class BaseToolContributionLayer(BaseFormalizationLayer, ABC):
    """Typed base for layers that contribute tools to the harness surface."""

    @abstractmethod
    def get_contributed_tools(self) -> Sequence[ToolDefinition]:
        """Return the tools contributed by this layer."""

    def get_formalization_tools(self) -> tuple[ToolDefinition, ...]:
        return tuple(self.get_contributed_tools())

    def _describe_identity(self) -> str:
        tools = tuple(self.get_contributed_tools())
        return self._compose_identity(
            what=(
                "This layer formalizes additional tools that should be attached to the harness "
                "because of the layer's own runtime contract."
            ),
            why=(
                "When a formalization concern depends on dedicated tools, those tools should be "
                "declared as part of the layer rather than smuggled in through unrelated setup code."
            ),
            how=(
                f"The layer contributes {len(tools)} tool(s): "
                f"{', '.join(tool.key for tool in tools) or 'none'}."
            ),
            intent=(
                "Keep the tool surface attributable to the formalization layer that owns it."
            ),
        )

    def _describe_contract(self) -> str:
        tool_lines = "\n".join(
            f"- {tool.key}: {tool.description}"
            for tool in self.get_contributed_tools()
        ) or "- No tools contributed."
        return (
            "This layer contributes tools to the harness runtime surface.\n\n"
            "Tools:\n"
            f"{tool_lines}"
        )

    def _describe_rules(self) -> Sequence[LayerRuleRecord]:
        if not tuple(self.get_contributed_tools()):
            return ()
        return (
            LayerRuleRecord(
                rule_id="TOOLS-CONTRIBUTED",
                description="This layer contributes additional tools to the harness surface.",
                enforced_at="get_parameter_sections",
                enforcement_type="inject",
            ),
        )

    def _describe_configuration(self) -> Mapping[str, Any]:
        return {"tool_keys": [tool.key for tool in self.get_contributed_tools()]}


__all__ = ["BaseToolContributionLayer"]
