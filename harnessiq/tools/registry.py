"""Deterministic registration and execution helpers for tools."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from harnessiq.shared.tools import RegisteredTool, ToolArguments, ToolDefinition, ToolResult


class DuplicateToolError(ValueError):
    """Raised when multiple tools claim the same public key."""


class UnknownToolError(KeyError):
    """Raised when a caller requests a tool key that is not registered."""


class ToolValidationError(ValueError):
    """Raised when runtime arguments violate the canonical tool schema."""


class ToolRegistry:
    """A deterministic in-memory registry for executable tools."""

    def __init__(self, tools: Iterable[RegisteredTool]) -> None:
        ordered_tools = tuple(tools)
        registry: dict[str, RegisteredTool] = {}
        for tool in ordered_tools:
            if tool.key in registry:
                message = f"Tool key '{tool.key}' is already registered."
                raise DuplicateToolError(message)
            registry[tool.key] = tool
        self._ordered_keys = tuple(tool.key for tool in ordered_tools)
        self._registry = registry

    def __contains__(self, tool_key: str) -> bool:
        return tool_key in self._registry

    def keys(self) -> tuple[str, ...]:
        """Return registered keys in stable order."""
        return self._ordered_keys

    def definitions(self, tool_keys: Sequence[str] | None = None) -> list[ToolDefinition]:
        """Return canonical tool definitions for all or selected tools."""
        selected = self.select(tool_keys) if tool_keys is not None else self._registry.values()
        return [tool.definition for tool in selected]

    def inspect(self, tool_keys: Sequence[str] | None = None) -> list[dict[str, object]]:
        """Return rich inspection payloads for all or selected tools."""
        selected = self.select(tool_keys) if tool_keys is not None else self._registry.values()
        return [tool.inspect() for tool in selected]

    def get(self, tool_key: str) -> RegisteredTool | None:
        """Look up a tool without throwing on missing keys."""
        return self._registry.get(tool_key)

    def require(self, tool_key: str) -> RegisteredTool:
        """Look up a tool and raise a clear error if it is missing."""
        tool = self.get(tool_key)
        if tool is None:
            message = f"Unknown tool key '{tool_key}'."
            raise UnknownToolError(message)
        return tool

    def select(self, tool_keys: Sequence[str]) -> list[RegisteredTool]:
        """Resolve a stable list of tools from public keys."""
        return [self.require(tool_key) for tool_key in tool_keys]

    def execute(self, tool_key: str, arguments: ToolArguments) -> ToolResult:
        """Execute a tool by public key."""
        tool = self.require(tool_key)
        _validate_arguments(tool.definition, arguments)
        return tool.execute(arguments)


def _validate_arguments(definition: ToolDefinition, arguments: ToolArguments) -> None:
    """Apply a small deterministic validation pass for the canonical schema."""
    required_keys = tuple(definition.input_schema.get("required", ()))
    missing_keys = [key for key in required_keys if key not in arguments]
    if missing_keys:
        missing = ", ".join(sorted(missing_keys))
        message = f"Tool '{definition.key}' is missing required arguments: {missing}."
        raise ToolValidationError(message)

    allows_additional = definition.input_schema.get("additionalProperties", True)
    if not allows_additional:
        allowed_keys = set(definition.input_schema.get("properties", {}))
        unexpected_keys = sorted(set(arguments) - allowed_keys)
        if unexpected_keys:
            unexpected = ", ".join(unexpected_keys)
            message = f"Tool '{definition.key}' received unexpected arguments: {unexpected}."
            raise ToolValidationError(message)


def create_builtin_registry() -> ToolRegistry:
    """Create the default registry for the initial built-in tool set."""
    from .builtin import BUILTIN_TOOLS

    return ToolRegistry(BUILTIN_TOOLS)
