"""Shared agent-context data models for future harness runtimes."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

AgentContextEntryKind = Literal["parameter", "message", "tool_call", "tool_result", "summary"]
AgentMessageRole = Literal["system", "user", "assistant"]


class _AgentContextEntryRequired(TypedDict):
    kind: AgentContextEntryKind


class AgentContextEntry(_AgentContextEntryRequired, total=False):
    """A normalized agent context-window entry."""

    role: AgentMessageRole
    content: str
    label: str
    tool_key: str
    tool_call_id: str
    arguments: dict[str, Any]
    output: Any
    metadata: dict[str, Any]


AgentContextWindow = list[AgentContextEntry]

__all__ = [
    "AgentContextEntry",
    "AgentContextEntryKind",
    "AgentContextWindow",
    "AgentMessageRole",
]
