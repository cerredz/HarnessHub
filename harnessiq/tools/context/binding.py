"""Agent-tool binding helpers for the context tool family."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from harnessiq.shared.agents import AgentToolExecutor
from harnessiq.shared.tools import RegisteredTool, ToolDefinition, ToolResult
from harnessiq.tools.registry import ToolRegistry


class BoundContextToolExecutor:
    """Merge BaseAgent-bound context tools with an existing executor."""

    def __init__(self, *, delegate: AgentToolExecutor, context_tools: Iterable[RegisteredTool]) -> None:
        self._delegate = delegate
        self._context_registry = ToolRegistry(context_tools)

    def definitions(self, tool_keys: Sequence[str] | None = None) -> list[ToolDefinition]:
        if tool_keys is None:
            delegate_definitions = self._delegate.definitions()
            context_definitions = self._context_registry.definitions()
            delegate_keys = {definition.key for definition in delegate_definitions}
            return [
                *delegate_definitions,
                *(definition for definition in context_definitions if definition.key not in delegate_keys),
            ]

        definitions: list[ToolDefinition] = []
        delegate_keys = set(getattr(self._delegate, "keys", lambda: ())())
        context_keys = set(self._context_registry.keys())
        for tool_key in tool_keys:
            if tool_key in context_keys:
                definitions.extend(self._context_registry.definitions([tool_key]))
                continue
            if tool_key in delegate_keys:
                definitions.extend(self._delegate.definitions([tool_key]))
                continue
            definitions.extend(self._delegate.definitions([tool_key]))
        return definitions

    def inspect(self, tool_keys: Sequence[str] | None = None) -> list[dict[str, Any]]:
        if tool_keys is None:
            payload: list[dict[str, Any]] = []
            inspector = getattr(self._delegate, "inspect", None)
            if callable(inspector):
                payload.extend(inspector())
            else:
                payload.extend(definition.inspect() for definition in self._delegate.definitions())
            payload.extend(self._context_registry.inspect())
            return payload

        payload: list[dict[str, Any]] = []
        inspector = getattr(self._delegate, "inspect", None)
        context_keys = set(self._context_registry.keys())
        delegate_keys = set(getattr(self._delegate, "keys", lambda: ())())
        for tool_key in tool_keys:
            if tool_key in context_keys:
                payload.extend(self._context_registry.inspect([tool_key]))
                continue
            if callable(inspector) and tool_key in delegate_keys:
                payload.extend(inspector([tool_key]))
                continue
            payload.extend(definition.inspect() for definition in self._delegate.definitions([tool_key]))
        return payload

    def execute(self, tool_key: str, arguments: dict[str, Any]) -> ToolResult:
        if tool_key in self._context_registry:
            return self._context_registry.execute(tool_key, arguments)
        return self._delegate.execute(tool_key, arguments)


__all__ = ["BoundContextToolExecutor"]
