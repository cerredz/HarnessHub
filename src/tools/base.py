"""Base executable tool abstractions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .schemas import ToolArguments, ToolDefinition, ToolResult


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
