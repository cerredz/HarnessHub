"""Core schemas shared by the tool registry and runtime."""

from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
from typing import Any

JsonObject = dict[str, Any]
ToolArguments = dict[str, Any]


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """Provider-agnostic metadata for a callable tool."""

    key: str
    name: str
    description: str
    input_schema: JsonObject

    def as_dict(self) -> JsonObject:
        """Return the canonical metadata without executable runtime state."""
        return {
            "key": self.key,
            "name": self.name,
            "description": self.description,
            "input_schema": deepcopy(self.input_schema),
        }


@dataclass(frozen=True, slots=True)
class ToolCall:
    """A concrete invocation request for a tool."""

    tool_key: str
    arguments: ToolArguments


@dataclass(frozen=True, slots=True)
class ToolResult:
    """A normalized local execution result."""

    tool_key: str
    output: Any
