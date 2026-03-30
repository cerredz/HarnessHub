"""
===============================================================================
File: harnessiq/tools/spawn_specialized_subagents/operations.py

What this file does:
- Exposes the `spawn_specialized_subagents` tool family for the HarnessIQ tool
  layer.
- In most packages this module is the bridge between provider-backed operations
  and the generic tool registration surface.
- Tool definitions for the spawn-specialized-subagents harness.

Use cases:
- Import this module when an agent or registry needs the
  `spawn_specialized_subagents` tool definitions.
- Read it to see which runtime operations are intentionally surfaced as tools.

How to use it:
- Call the exported factory helpers from
  `harnessiq/tools/spawn_specialized_subagents` and merge the resulting tools
  into a registry.

Intent:
- Keep the public `spawn_specialized_subagents` tool surface small, explicit,
  and separate from provider implementation details.
===============================================================================
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from harnessiq.shared.tools import (
    RegisteredTool,
    SPAWN_INTEGRATE_RESULTS,
    SPAWN_PLAN_ASSIGNMENTS,
    SPAWN_RUN_ASSIGNMENT,
    ToolArguments,
    ToolDefinition,
)

SpawnToolHandler = Callable[[ToolArguments], dict[str, Any]]


def build_plan_assignments_tool_definition() -> ToolDefinition:
    """Return the canonical tool definition for delegation planning."""
    return ToolDefinition(
        key=SPAWN_PLAN_ASSIGNMENTS,
        name="plan_assignments",
        description="Create or refresh the current local step and bounded worker assignments.",
        input_schema={"type": "object", "properties": {}, "required": [], "additionalProperties": False},
    )


def build_run_assignment_tool_definition() -> ToolDefinition:
    """Return the canonical tool definition for one worker assignment execution."""
    return ToolDefinition(
        key=SPAWN_RUN_ASSIGNMENT,
        name="run_assignment",
        description="Execute one worker assignment by assignment id and persist the structured result.",
        input_schema={
            "type": "object",
            "properties": {"assignment_id": {"type": "string"}},
            "required": ["assignment_id"],
            "additionalProperties": False,
        },
    )


def build_integrate_results_tool_definition() -> ToolDefinition:
    """Return the canonical tool definition for orchestration result integration."""
    return ToolDefinition(
        key=SPAWN_INTEGRATE_RESULTS,
        name="integrate_results",
        description="Integrate collected worker outputs into one coherent final response.",
        input_schema={"type": "object", "properties": {}, "required": [], "additionalProperties": False},
    )


def create_spawn_specialized_subagents_tools(
    *,
    plan_assignments_handler: SpawnToolHandler,
    run_assignment_handler: SpawnToolHandler,
    integrate_results_handler: SpawnToolHandler,
) -> tuple[RegisteredTool, ...]:
    """Return the spawn-specialized-subagents harness tools with runtime handlers injected."""
    return (
        RegisteredTool(
            definition=build_plan_assignments_tool_definition(),
            handler=plan_assignments_handler,
        ),
        RegisteredTool(
            definition=build_run_assignment_tool_definition(),
            handler=run_assignment_handler,
        ),
        RegisteredTool(
            definition=build_integrate_results_tool_definition(),
            handler=integrate_results_handler,
        ),
    )


__all__ = [
    "build_integrate_results_tool_definition",
    "build_plan_assignments_tool_definition",
    "build_run_assignment_tool_definition",
    "create_spawn_specialized_subagents_tools",
]
