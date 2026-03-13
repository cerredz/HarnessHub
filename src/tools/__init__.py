"""Canonical tool primitives for HarnessHub."""

from src.shared.tools import (
    ADD_NUMBERS,
    ECHO_TEXT,
    JsonObject,
    RegisteredTool,
    ToolArguments,
    ToolCall,
    ToolDefinition,
    ToolHandler,
    ToolResult,
)

from .builtin import BUILTIN_TOOLS
from .registry import ToolRegistry, create_builtin_registry

__all__ = [
    "ADD_NUMBERS",
    "BUILTIN_TOOLS",
    "ECHO_TEXT",
    "JsonObject",
    "RegisteredTool",
    "ToolArguments",
    "ToolCall",
    "ToolDefinition",
    "ToolHandler",
    "ToolResult",
    "ToolRegistry",
    "create_builtin_registry",
]
