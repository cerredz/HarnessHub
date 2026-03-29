"""Universal base contract for all formalization layer interfaces.

This module defines the one abstraction every formalization layer shares. The
design goal is to make formalization layers optional, composable, and
self-documenting:

- optional, because a harness should still work without any formalization layer
- composable, because multiple layers can participate without tightly coupling
- self-documenting, because the interface itself should explain what it is doing

The base class deliberately provides no-op runtime hooks and a default
documentation pipeline. Concrete layer families only override the specific
runtime seams and description methods they care about.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from harnessiq.shared.agents import AgentParameterSection, AgentPauseSignal
from harnessiq.shared.formalization import (
    BudgetSpec,
    FieldSpec,
    FormalizationDescription,
    LayerRuleRecord,
)
from harnessiq.shared.tools import ToolCall, ToolDefinition, ToolResult


class BaseFormalizationLayer(ABC):
    """Universal formalization-layer contract with self-documenting defaults.

    A formalization layer is an injectable runtime surface that can:

    - add deterministic structure to the harness
    - contribute context-window sections
    - shape tool visibility
    - enforce lifecycle rules through hook participation

    The base class assumes the harness owns the runtime loop. The layer only
    exposes hook points and documentation helpers that the harness may call.
    """

    @property
    def layer_id(self) -> str:
        """Return the stable public identifier for this layer instance."""
        return self.__class__.__name__

    def describe(self) -> FormalizationDescription:
        """Return the structured self-description for this layer."""
        return FormalizationDescription(
            layer_id=self.layer_id,
            identity=self._describe_identity(),
            contract=self._describe_contract(),
            rules=tuple(self._describe_rules()),
            configuration=dict(self._describe_configuration()),
        )

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        """Return formalization-owned context sections for the model window."""
        return (
            AgentParameterSection(
                title=f"Formalization: {self.layer_id}",
                content=self.describe().render_for_agent(),
            ),
        )

    def augment_system_prompt(self, system_prompt: str) -> str:
        """Return the system prompt after this layer's deterministic changes."""
        return system_prompt

    def get_formalization_tools(self) -> tuple[ToolDefinition, ...]:
        """Return any tools contributed by this formalization layer."""
        return ()

    def filter_tool_keys(self, tool_keys: Sequence[str]) -> tuple[str, ...]:
        """Return the model-visible tool keys after this layer's filtering."""
        return tuple(tool_keys)

    def on_agent_prepare(self, *, agent_name: str, memory_path: str | Path) -> None:
        """Run deterministic setup before the harness enters its main loop."""
        del agent_name, memory_path

    def on_tool_call(
        self,
        tool_call: ToolCall,
    ) -> ToolCall | ToolResult | AgentPauseSignal:
        """Inspect or transform a tool call before the harness executes it."""
        return tool_call

    def on_tool_result(self, result: ToolResult) -> ToolResult:
        """Inspect or transform a tool result before the harness records it."""
        return result

    def on_tool_result_event(self, tool_call: ToolCall, result: ToolResult) -> ToolResult:
        """Inspect a tool result with access to the originating tool call."""
        del tool_call
        return self.on_tool_result(result)

    def on_pre_reset(self) -> None:
        """Run deterministic work immediately before the context resets."""

    def on_post_reset(self) -> None:
        """Run deterministic work immediately after the context resets."""

    def _describe_identity(self) -> str:
        """Return default identity prose for a generic formalization layer."""
        rules = tuple(self._describe_rules())
        declared_hooks = sorted({rule.enforced_at for rule in rules})
        hook_summary = ", ".join(declared_hooks) if declared_hooks else "no explicit hooks"
        return self._compose_identity(
            what=(
                f"{self.layer_id} is a formalization layer that can inject context, "
                "shape runtime behavior, and expose deterministic structure to a harness."
            ),
            why=(
                "Formalization layers make optional harness behavior explicit instead of "
                "burying it inside ad hoc prompt text or scattered runtime conditionals."
            ),
            how=(
                f"This layer currently declares {len(rules)} auditable rule(s) across {hook_summary}. "
                "A harness can call the layer hooks to enforce the declared behavior in Python code."
            ),
            intent=(
                "Give both developers and the agent a single self-documenting source of truth "
                "for what this layer means and where it acts."
            ),
        )

    @abstractmethod
    def _describe_contract(self) -> str:
        """Return the behavioral contract for this layer."""

    @abstractmethod
    def _describe_rules(self) -> Sequence[LayerRuleRecord]:
        """Return the auditable rules declared by this layer."""

    @abstractmethod
    def _describe_configuration(self) -> Mapping[str, Any]:
        """Return the active configuration snapshot for this layer."""

    @staticmethod
    def _compose_identity(*, what: str, why: str, how: str, intent: str) -> str:
        """Render one continuous identity string covering purpose and behavior."""
        return (
            f"{what} {why} {how} {intent}"
        )

    @staticmethod
    def _format_field(field: FieldSpec) -> str:
        """Render one field spec for docs shown to developers or the model."""
        required = "required" if field.required else "optional"
        default = "" if field.default is None else f" Default: {field.default!r}."
        description = BaseFormalizationLayer._ensure_sentence(field.description)
        return f"- {field.name} ({field.field_type}, {required}): {description}{default}"

    @staticmethod
    def _format_budget(budget: BudgetSpec | None) -> str:
        """Render a human-readable execution budget summary."""
        if budget is None:
            return "No explicit execution budget declared."
        parts: list[str] = []
        if budget.max_tokens is not None:
            parts.append(f"{budget.max_tokens} tokens")
        if budget.max_resets is not None:
            parts.append(f"{budget.max_resets} resets")
        if budget.max_wall_seconds is not None:
            parts.append(f"{budget.max_wall_seconds:g}s wall time")
        return ", ".join(parts) if parts else "No explicit execution budget declared."

    @staticmethod
    def _filter_with_patterns(
        tool_keys: Sequence[str],
        patterns: Sequence[str],
    ) -> tuple[str, ...]:
        """Apply fnmatch patterns to a visible tool-key surface."""
        if not patterns:
            return tuple(tool_keys)
        return tuple(
            tool_key
            for tool_key in tool_keys
            if any(fnmatch(tool_key, pattern) for pattern in patterns)
        )

    @staticmethod
    def _ensure_sentence(text: str) -> str:
        """Normalize prose snippets so helper-generated docs read cleanly."""
        stripped = text.strip()
        if not stripped:
            return stripped
        if stripped[-1] in ".!?":
            return stripped
        return f"{stripped}."


__all__ = ["BaseFormalizationLayer"]
