"""Shared helper functions for provider-backed agent harnesses."""

from __future__ import annotations

import json
from typing import Any, Iterable, Mapping, Sequence

from harnessiq.shared.tools import RegisteredTool, ToolDefinition

DEFAULT_PROVIDER_AGENT_IDENTITY = (
    "A disciplined provider-backed operations agent that plans carefully and executes external "
    "work only through verified tool calls."
)


def merge_registered_tools(*tool_groups: Iterable[RegisteredTool]) -> tuple[RegisteredTool, ...]:
    """Return registered tools in stable order while preserving the first definition for each key."""
    ordered_keys: list[str] = []
    merged: dict[str, RegisteredTool] = {}
    for tool_group in tool_groups:
        for tool in tool_group:
            if tool.key in merged:
                continue
            ordered_keys.append(tool.key)
            merged[tool.key] = tool
    return tuple(merged[key] for key in ordered_keys)


def summarize_tool_description(tool: ToolDefinition) -> str:
    """Return the first descriptive line for a tool definition."""
    first_line = tool.description.splitlines()[0].strip()
    return first_line or tool.name


def extract_operation_names(tool: ToolDefinition) -> tuple[str, ...]:
    """Extract the canonical operation enum from a request-style tool definition."""
    properties = tool.input_schema.get("properties", {})
    if not isinstance(properties, Mapping):
        return ()
    operation_schema = properties.get("operation")
    if not isinstance(operation_schema, Mapping):
        return ()
    enum_values = operation_schema.get("enum")
    if not isinstance(enum_values, Sequence) or isinstance(enum_values, (str, bytes)):
        return ()
    return tuple(str(value) for value in enum_values)


def render_tool_operation_summary(
    tool: ToolDefinition,
    *,
    sample_size: int = 6,
) -> str:
    """Render a one-line summary of the tool plus a compact operation sample when available."""
    summary = summarize_tool_description(tool)
    operation_names = extract_operation_names(tool)
    if not operation_names:
        return summary
    sample = ", ".join(f"`{name}`" for name in operation_names[:sample_size])
    remaining = len(operation_names) - min(len(operation_names), sample_size)
    suffix = f", +{remaining} more" if remaining > 0 else ""
    return f"{summary} Supported operations: {sample}{suffix}."


def render_redacted_provider_credentials(
    redacted_payload: Mapping[str, Any],
    *,
    allowed_operations: Sequence[str] | None = None,
    operation_sample_size: int = 8,
) -> str:
    """Render a redacted provider credential summary suitable for a parameter section."""
    payload = dict(redacted_payload)
    if allowed_operations is not None:
        normalized_operations = tuple(dict.fromkeys(str(name) for name in allowed_operations))
        payload["allowed_operation_count"] = len(normalized_operations)
        payload["allowed_operation_sample"] = list(normalized_operations[:operation_sample_size])
    return json.dumps(payload, indent=2, sort_keys=True, default=str)


def build_provider_tool_system_prompt(
    *,
    identity: str,
    objective: str,
    transport_guidance: str,
    tools: Sequence[ToolDefinition],
    behavioral_rules: Sequence[str],
    additional_instructions: str | None = None,
) -> str:
    """Build the standard sectioned system prompt for provider-backed agents."""
    tool_lines = [f"- {tool.name}: {render_tool_operation_summary(tool)}" for tool in tools]
    normalized_rules = [_normalize_rule(rule) for rule in behavioral_rules if rule.strip()]
    sections = [
        "[IDENTITY]",
        identity.strip(),
        "[GOAL]",
        objective.strip(),
        "[TRANSPORT]",
        transport_guidance.strip(),
        "[TOOLS]",
        "\n".join(tool_lines),
        "[BEHAVIORAL RULES]",
        "\n".join(normalized_rules),
    ]
    if additional_instructions and additional_instructions.strip():
        sections.extend(["[ADDITIONAL INSTRUCTIONS]", additional_instructions.strip()])
    return "\n\n".join(section for section in sections if section)


def _normalize_rule(rule: str) -> str:
    stripped = rule.strip()
    if stripped.startswith("-"):
        return stripped
    return f"- {stripped}"


__all__ = [
    "DEFAULT_PROVIDER_AGENT_IDENTITY",
    "build_provider_tool_system_prompt",
    "extract_operation_names",
    "merge_registered_tools",
    "render_redacted_provider_credentials",
    "render_tool_operation_summary",
    "summarize_tool_description",
]
