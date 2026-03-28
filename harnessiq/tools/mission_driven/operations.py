"""Tool definitions for the mission-driven harness."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from harnessiq.shared.tools import (
    MISSION_CREATE_CHECKPOINT,
    MISSION_INITIALIZE_ARTIFACT,
    MISSION_RECORD_UPDATES,
    RegisteredTool,
    ToolArguments,
    ToolDefinition,
)

MissionToolHandler = Callable[[ToolArguments], dict[str, Any]]


def build_initialize_artifact_tool_definition() -> ToolDefinition:
    """Return the canonical tool definition for mission artifact initialization."""
    return ToolDefinition(
        key=MISSION_INITIALIZE_ARTIFACT,
        name="initialize_artifact",
        description="Initialize the full mission artifact from the configured mission goal and type.",
        input_schema={"type": "object", "properties": {}, "required": [], "additionalProperties": False},
    )


def build_record_updates_tool_definition() -> ToolDefinition:
    """Return the canonical tool definition for mission artifact updates."""
    return ToolDefinition(
        key=MISSION_RECORD_UPDATES,
        name="record_updates",
        description=(
            "Persist task, progress, durable facts, decisions, file-manifest entries, research notes, "
            "tests, artifacts, queue updates, and mission-status changes into the mission artifact."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "task_updates": {"type": "array", "items": {"type": "object"}},
                "progress_events": {"type": "array", "items": {"type": "object"}},
                "memory_facts": {"type": "array", "items": {"type": "object"}},
                "decisions": {"type": "array", "items": {"type": "object"}},
                "errors": {"type": "array", "items": {"type": "object"}},
                "feedback": {"type": "array", "items": {"type": "object"}},
                "test_results": {"type": "array", "items": {"type": "object"}},
                "artifacts": {"type": "array", "items": {"type": "object"}},
                "file_records": {"type": "array", "items": {"type": "object"}},
                "research_entries": {"type": "array", "items": {"type": "object"}},
                "tool_calls": {"type": "array", "items": {"type": "object"}},
                "next_actions": {"type": "array", "items": {"type": "string"}},
                "mission_status": {"type": "string"},
            },
            "required": [],
            "additionalProperties": False,
        },
    )


def build_create_checkpoint_tool_definition() -> ToolDefinition:
    """Return the canonical tool definition for mission checkpoints."""
    return ToolDefinition(
        key=MISSION_CREATE_CHECKPOINT,
        name="create_checkpoint",
        description="Create a checkpoint snapshot of the current mission artifact with resume instructions.",
        input_schema={
            "type": "object",
            "properties": {
                "checkpoint_name": {"type": "string"},
                "resume_instructions": {"type": "string"},
            },
            "required": ["checkpoint_name", "resume_instructions"],
            "additionalProperties": False,
        },
    )


def create_mission_driven_tools(
    *,
    initialize_artifact_handler: MissionToolHandler,
    record_updates_handler: MissionToolHandler,
    create_checkpoint_handler: MissionToolHandler,
) -> tuple[RegisteredTool, ...]:
    """Return the mission-driven harness tools with runtime handlers injected."""
    return (
        RegisteredTool(
            definition=build_initialize_artifact_tool_definition(),
            handler=initialize_artifact_handler,
        ),
        RegisteredTool(
            definition=build_record_updates_tool_definition(),
            handler=record_updates_handler,
        ),
        RegisteredTool(
            definition=build_create_checkpoint_tool_definition(),
            handler=create_checkpoint_handler,
        ),
    )


__all__ = [
    "build_create_checkpoint_tool_definition",
    "build_initialize_artifact_tool_definition",
    "build_record_updates_tool_definition",
    "create_mission_driven_tools",
]
