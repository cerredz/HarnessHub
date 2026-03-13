"""Shared tool constants, aliases, and runtime data models."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Protocol

JsonObject = dict[str, Any]
ToolArguments = dict[str, Any]

ECHO_TEXT = "core.echo_text"
ADD_NUMBERS = "core.add_numbers"
REMOVE_TOOL_RESULTS = "context.remove_tool_results"
REMOVE_TOOLS = "context.remove_tools"
HEAVY_COMPACTION = "context.heavy_compaction"
LOG_COMPACTION = "context.log_compaction"


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


class ToolHandler(Protocol):
    """Callable runtime contract for built-in and custom tools."""

    def __call__(self, arguments: ToolArguments) -> object:
        """Execute the tool with normalized arguments."""


@dataclass(frozen=True, slots=True)
class RegisteredTool:
    """Bind canonical tool metadata to a local executable handler."""

    definition: ToolDefinition
    handler: ToolHandler

    @property
    def key(self) -> str:
        return self.definition.key

    def execute(self, arguments: ToolArguments) -> ToolResult:
        """Run the tool handler and normalize its output."""
        return ToolResult(tool_key=self.key, output=self.handler(arguments))


__all__ = [
    "ADD_NUMBERS",
    "ECHO_TEXT",
    "HEAVY_COMPACTION",
    "JsonObject",
    "LOG_COMPACTION",
    "REMOVE_TOOL_RESULTS",
    "REMOVE_TOOLS",
    "RegisteredTool",
    "ToolArguments",
    "ToolCall",
    "ToolDefinition",
    "ToolHandler",
    "ToolResult",
]
