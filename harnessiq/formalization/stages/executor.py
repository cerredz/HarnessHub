from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from harnessiq.shared.agents import AgentToolExecutor
from harnessiq.shared.tools import RegisteredTool, ToolDefinition, ToolResult
from harnessiq.tools.registry import ToolRegistry


class StageAwareToolExecutor:
    """Wrap a base tool executor with a hot-swappable stage tool layer."""

    def __init__(
        self,
        *,
        base: AgentToolExecutor,
        initial_stage_tools: Sequence[RegisteredTool] = (),
    ) -> None:
        self._base = base
        self._stage_registry = ToolRegistry(initial_stage_tools) if initial_stage_tools else None

    def swap_stage_tools(self, stage_tools: Sequence[RegisteredTool]) -> None:
        """Replace the active stage tool layer."""
        if stage_tools:
            self._stage_registry = ToolRegistry(stage_tools)
            return
        self._stage_registry = None

    def definitions(self, tool_keys: Sequence[str] | None = None) -> list[ToolDefinition]:
        if tool_keys is None:
            base_definitions = self._base.definitions()
            if self._stage_registry is None:
                return base_definitions
            stage_definitions = self._stage_registry.definitions()
            stage_keys = {definition.key for definition in stage_definitions}
            return [*stage_definitions, *(definition for definition in base_definitions if definition.key not in stage_keys)]

        definitions: list[ToolDefinition] = []
        stage_keys = set(self._stage_registry.keys() if self._stage_registry else ())
        base_keys = set(getattr(self._base, "keys", lambda: ())())
        for key in tool_keys:
            if key in stage_keys:
                definitions.extend(self._stage_registry.definitions([key]))
            elif key in base_keys:
                definitions.extend(self._base.definitions([key]))
        return definitions

    def execute(self, tool_key: str, arguments: dict[str, Any]) -> ToolResult:
        if self._stage_registry is not None and tool_key in self._stage_registry:
            return self._stage_registry.execute(tool_key, arguments)
        return self._base.execute(tool_key, arguments)

    def inspect(self, tool_keys: Sequence[str] | None = None) -> list[dict[str, Any]]:
        """Return rich inspection metadata for the stage and base tool layers."""
        base_inspect = getattr(self._base, "inspect", None)
        stage_keys = set(self._stage_registry.keys() if self._stage_registry else ())
        if tool_keys is None:
            base_payload = base_inspect(tool_keys) if callable(base_inspect) else []
        else:
            base_tool_keys = tuple(key for key in tool_keys if key not in stage_keys)
            base_payload = base_inspect(base_tool_keys) if callable(base_inspect) else []
        if self._stage_registry is None:
            return base_payload
        stage_tool_keys = None if tool_keys is None else tuple(key for key in tool_keys if key in stage_keys)
        stage_payload = self._stage_registry.inspect(stage_tool_keys)
        stage_payload_keys = {item["key"] for item in stage_payload}
        return [*stage_payload, *(item for item in base_payload if item["key"] not in stage_payload_keys)]

    @property
    def base(self) -> AgentToolExecutor:
        """Return the wrapped base executor."""
        return self._base
