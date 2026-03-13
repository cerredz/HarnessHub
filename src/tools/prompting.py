"""Prompt-generation tools for agent system prompts."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from src.shared.agents import AgentContextEntry, AgentContextWindow
from src.shared.tools import PROMPT_CREATE_SYSTEM_PROMPT, RegisteredTool, ToolArguments, ToolDefinition

_ALLOWED_CONTEXT_KINDS = frozenset({"parameter", "message", "tool_call", "tool_result", "summary"})
_CONTEXT_WINDOW_PROPERTY: dict[str, object] = {
    "type": "array",
    "description": "An ordered list of normalized agent context entries.",
    "items": {"type": "object"},
}


def create_system_prompt(
    role: str,
    objective: str,
    context_window: list[Mapping[str, Any]],
    *,
    agent_name: str | None = None,
    tone: str | None = None,
    instructions: Sequence[str] = (),
    constraints: Sequence[str] = (),
    available_tools: Sequence[Mapping[str, Any]] = (),
    max_context_entries: int = 8,
    max_entry_chars: int = 300,
) -> str:
    """Create a structured system prompt from explicit inputs and current context."""
    role = role.strip()
    objective = objective.strip()
    if not role:
        raise ValueError("role must not be empty.")
    if not objective:
        raise ValueError("objective must not be empty.")
    if max_context_entries < 0:
        raise ValueError("max_context_entries must be greater than or equal to zero.")
    if max_entry_chars <= 0:
        raise ValueError("max_entry_chars must be greater than zero.")

    normalized_context = _normalize_context_window(context_window)
    normalized_instructions = _normalize_string_sequence(instructions, label="instructions")
    normalized_constraints = _normalize_string_sequence(constraints, label="constraints")
    normalized_tools = _normalize_tool_metadata(available_tools)

    intro = f"You are {agent_name}, a {role}." if agent_name else f"You are a {role}."
    if tone:
        intro = f"{intro} Use a {tone} tone."

    sections = [intro, _render_section("PRIMARY OBJECTIVE", objective)]
    if normalized_instructions:
        sections.append(_render_bullet_section("OPERATING INSTRUCTIONS", normalized_instructions))
    if normalized_constraints:
        sections.append(_render_bullet_section("CONSTRAINTS", normalized_constraints))
    if normalized_tools:
        sections.append(_render_bullet_section("AVAILABLE TOOLS", normalized_tools))

    context_summary = _render_context_window(normalized_context, max_context_entries=max_context_entries, max_entry_chars=max_entry_chars)
    if context_summary:
        sections.append(_render_section("CONTEXT WINDOW", context_summary))

    sections.append(
        _render_section(
            "EXECUTION NOTES",
            "Base decisions on the supplied context window, prioritize durable parameter entries, and avoid inventing facts that are not present in the provided context or tool outputs.",
        )
    )
    return "\n\n".join(section for section in sections if section)


def create_prompt_tools() -> tuple[RegisteredTool, ...]:
    """Return the registered tool set for prompt generation."""
    return (
        RegisteredTool(
            definition=ToolDefinition(
                key=PROMPT_CREATE_SYSTEM_PROMPT,
                name="create_system_prompt",
                description="Generate a system prompt string from explicit inputs and a context window.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "role": {"type": "string", "description": "Primary role the agent should adopt."},
                        "objective": {"type": "string", "description": "The main goal the system prompt should optimize for."},
                        "context_window": _context_window_property(),
                        "agent_name": {"type": "string", "description": "Optional agent name used in the prompt introduction."},
                        "tone": {"type": "string", "description": "Optional tone guidance such as precise, calm, or assertive."},
                        "instructions": {
                            "type": "array",
                            "description": "Ordered operating instructions to include.",
                            "items": {"type": "string"},
                        },
                        "constraints": {
                            "type": "array",
                            "description": "Ordered constraints or guardrails to include.",
                            "items": {"type": "string"},
                        },
                        "available_tools": {
                            "type": "array",
                            "description": "Optional tool metadata to mention in the prompt.",
                            "items": {"type": "object"},
                        },
                        "max_context_entries": {
                            "type": "integer",
                            "description": "Maximum number of non-parameter context entries to render into the prompt.",
                        },
                        "max_entry_chars": {
                            "type": "integer",
                            "description": "Maximum number of characters to keep from any rendered context item.",
                        },
                    },
                    "required": ["role", "objective", "context_window"],
                    "additionalProperties": False,
                },
            ),
            handler=_create_system_prompt_tool,
        ),
    )


def _create_system_prompt_tool(arguments: ToolArguments) -> dict[str, str]:
    role = _require_string(arguments, "role")
    objective = _require_string(arguments, "objective")
    context_window = _require_context_window(arguments, "context_window")
    agent_name = _require_optional_string(arguments, "agent_name")
    tone = _require_optional_string(arguments, "tone")
    instructions = _require_string_sequence(arguments, "instructions", default=())
    constraints = _require_string_sequence(arguments, "constraints", default=())
    available_tools = _require_mapping_sequence(arguments, "available_tools", default=())
    max_context_entries = _require_int(arguments, "max_context_entries", default=8)
    max_entry_chars = _require_int(arguments, "max_entry_chars", default=300)
    return {
        "system_prompt": create_system_prompt(
            role,
            objective,
            context_window,
            agent_name=agent_name,
            tone=tone,
            instructions=instructions,
            constraints=constraints,
            available_tools=available_tools,
            max_context_entries=max_context_entries,
            max_entry_chars=max_entry_chars,
        )
    }


def _normalize_context_window(context_window: list[Mapping[str, Any]]) -> AgentContextWindow:
    normalized: AgentContextWindow = []
    for index, entry in enumerate(context_window):
        if not isinstance(entry, Mapping):
            raise ValueError(f"Context entry at index {index} must be a mapping.")
        kind = entry.get("kind")
        if kind not in _ALLOWED_CONTEXT_KINDS:
            raise ValueError(f"Unsupported context entry kind '{kind}' at index {index}.")
        normalized.append(deepcopy(dict(entry)))
    return normalized


def _normalize_tool_metadata(available_tools: Sequence[Mapping[str, Any]]) -> list[str]:
    rendered: list[str] = []
    for index, tool in enumerate(available_tools):
        if not isinstance(tool, Mapping):
            raise ValueError(f"Tool metadata at index {index} must be a mapping.")
        name = tool.get("name") or tool.get("key") or f"tool_{index + 1}"
        description = tool.get("description")
        if description is None:
            rendered.append(str(name))
        else:
            rendered.append(f"{name}: {description}")
    return rendered


def _render_context_window(
    context_window: AgentContextWindow,
    *,
    max_context_entries: int,
    max_entry_chars: int,
) -> str:
    parameters = [entry for entry in context_window if entry["kind"] == "parameter"]
    recent_entries = [entry for entry in context_window if entry["kind"] != "parameter"]
    if max_context_entries:
        recent_entries = recent_entries[-max_context_entries:]
    else:
        recent_entries = []

    lines: list[str] = []
    if parameters:
        lines.append("Durable parameters:")
        for entry in parameters:
            label = str(entry.get("label", "Parameter"))
            content = _preview(entry.get("content", ""), max_chars=max_entry_chars)
            lines.append(f"- {label}: {content}")
    if recent_entries:
        if lines:
            lines.append("")
        lines.append("Recent context:")
        lines.extend(_render_recent_entry(entry, max_entry_chars=max_entry_chars) for entry in recent_entries)
    return "\n".join(lines)


def _render_recent_entry(entry: AgentContextEntry, *, max_entry_chars: int) -> str:
    kind = entry["kind"]
    if kind == "message":
        role = entry.get("role", "assistant")
        return f"- Message ({role}): {_preview(entry.get('content', ''), max_chars=max_entry_chars)}"
    if kind == "tool_call":
        tool_key = entry.get("tool_key", "tool")
        arguments = entry.get("arguments", entry.get("content", ""))
        return f"- Tool call ({tool_key}): {_preview(arguments, max_chars=max_entry_chars)}"
    if kind == "tool_result":
        tool_key = entry.get("tool_key", "tool")
        output = entry.get("output", entry.get("content", ""))
        return f"- Tool result ({tool_key}): {_preview(output, max_chars=max_entry_chars)}"
    return f"- Summary: {_preview(entry.get('content', ''), max_chars=max_entry_chars)}"


def _render_section(title: str, body: str) -> str:
    return f"[{title}]\n{body.strip()}"


def _render_bullet_section(title: str, items: Sequence[str]) -> str:
    body = "\n".join(f"- {item}" for item in items)
    return _render_section(title, body)


def _preview(value: Any, *, max_chars: int) -> str:
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, sort_keys=True, default=str)
    collapsed = " ".join(text.split())
    if len(collapsed) <= max_chars:
        return collapsed
    return f"{collapsed[: max_chars - 3]}..."


def _context_window_property() -> dict[str, object]:
    return deepcopy(_CONTEXT_WINDOW_PROPERTY)


def _require_context_window(arguments: ToolArguments, key: str) -> list[Mapping[str, Any]]:
    value = arguments[key]
    if not isinstance(value, list):
        raise ValueError(f"The '{key}' argument must be a list of context entries.")
    return value


def _require_string(arguments: ToolArguments, key: str) -> str:
    value = arguments[key]
    if not isinstance(value, str):
        raise ValueError(f"The '{key}' argument must be a string.")
    return value


def _require_optional_string(arguments: ToolArguments, key: str) -> str | None:
    if key not in arguments or arguments[key] is None:
        return None
    value = arguments[key]
    if not isinstance(value, str):
        raise ValueError(f"The '{key}' argument must be a string when provided.")
    return value


def _require_string_sequence(
    arguments: ToolArguments,
    key: str,
    *,
    default: Sequence[str],
) -> Sequence[str]:
    if key not in arguments:
        return default
    value = arguments[key]
    if not isinstance(value, list):
        raise ValueError(f"The '{key}' argument must be a list of strings.")
    return _normalize_string_sequence(value, label=key)


def _require_mapping_sequence(
    arguments: ToolArguments,
    key: str,
    *,
    default: Sequence[Mapping[str, Any]],
) -> Sequence[Mapping[str, Any]]:
    if key not in arguments:
        return default
    value = arguments[key]
    if not isinstance(value, list):
        raise ValueError(f"The '{key}' argument must be a list of objects.")
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise ValueError(f"The '{key}' argument item at index {index} must be an object.")
    return value


def _normalize_string_sequence(values: Sequence[str], *, label: str) -> list[str]:
    normalized: list[str] = []
    for index, value in enumerate(values):
        if not isinstance(value, str):
            raise ValueError(f"The '{label}' item at index {index} must be a string.")
        normalized.append(value)
    return normalized


def _require_int(arguments: ToolArguments, key: str, *, default: int) -> int:
    if key not in arguments:
        return default
    value = arguments[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"The '{key}' argument must be an integer.")
    return value


__all__ = ["create_prompt_tools", "create_system_prompt"]

