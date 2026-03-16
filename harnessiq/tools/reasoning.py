"""Injectable reasoning tools for structured agent reasoning prompt injection."""

from __future__ import annotations

from harnessiq.shared.tools import (
    REASON_BRAINSTORM,
    REASON_CHAIN_OF_THOUGHT,
    REASON_CRITIQUE,
    RegisteredTool,
    ToolArguments,
    ToolDefinition,
)

_BRAINSTORM_COUNT_MIN = 5
_BRAINSTORM_COUNT_MAX = 25
_BRAINSTORM_COUNT_DEFAULT = 10
_COT_STEPS_MIN = 3
_COT_STEPS_MAX = 10
_COT_STEPS_DEFAULT = 5


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def brainstorm(arguments: ToolArguments) -> dict[str, str]:
    """Inject a brainstorm reasoning instruction into the agent's context window."""
    topic = _require_string(arguments, "topic")
    count = _optional_int(arguments, "count", _BRAINSTORM_COUNT_DEFAULT)
    if not (_BRAINSTORM_COUNT_MIN <= count <= _BRAINSTORM_COUNT_MAX):
        raise ValueError(
            f"'count' must be between {_BRAINSTORM_COUNT_MIN} and {_BRAINSTORM_COUNT_MAX}, got {count}."
        )
    context = _optional_string(arguments, "context")
    constraints = _optional_string(arguments, "constraints")

    lines = [
        "[REASONING: BRAINSTORM]",
        f"Topic: {topic}",
        f"Generate {count} distinct ideas.",
    ]
    if context:
        lines.append(f"Context: {context}")
    if constraints:
        lines.append(f"Constraints: {constraints}")
    lines += [
        "",
        f"For each of the {count} ideas, provide:",
        "  - A concise title",
        "  - A one-sentence rationale",
        "  - An estimated impact (low / medium / high)",
        "",
        "Output your reasoning tokens now. Think through each idea carefully before "
        "committing to it. After completing the brainstorm, identify the single strongest "
        "idea and state why you selected it.",
    ]
    return {"reasoning_instruction": "\n".join(lines)}


def chain_of_thought(arguments: ToolArguments) -> dict[str, str]:
    """Inject a chain-of-thought reasoning instruction into the agent's context window."""
    task = _require_string(arguments, "task")
    steps = _optional_int(arguments, "steps", _COT_STEPS_DEFAULT)
    if not (_COT_STEPS_MIN <= steps <= _COT_STEPS_MAX):
        raise ValueError(
            f"'steps' must be between {_COT_STEPS_MIN} and {_COT_STEPS_MAX}, got {steps}."
        )
    context = _optional_string(arguments, "context")

    lines = [
        "[REASONING: CHAIN OF THOUGHT]",
        f"Task: {task}",
        f"Reason through this in {steps} explicit steps.",
    ]
    if context:
        lines.append(f"Context: {context}")
    lines += [
        "",
        f"Work through exactly {steps} steps. For each step:",
        "  - State what you are reasoning about",
        "  - Present your reasoning",
        "  - State your conclusion for that step",
        "",
        "Output your reasoning tokens now. Do not skip steps or combine them. "
        "After completing all steps, state your final conclusion.",
    ]
    return {"reasoning_instruction": "\n".join(lines)}


def critique(arguments: ToolArguments) -> dict[str, str]:
    """Inject a critique reasoning instruction into the agent's context window."""
    content = _require_string(arguments, "content")
    raw_aspects = arguments.get("aspects")
    aspects: list[str]
    if raw_aspects is not None:
        if not isinstance(raw_aspects, list) or not all(isinstance(a, str) for a in raw_aspects):
            raise ValueError("'aspects' must be a list of strings when provided.")
        aspects = [str(a) for a in raw_aspects]
        if not aspects:
            raise ValueError("'aspects' must contain at least one entry when provided.")
    else:
        aspects = ["correctness", "clarity", "completeness", "potential improvements"]

    # Truncate content preview to keep the instruction concise
    preview = content if len(content) <= 300 else content[:297] + "..."

    lines = [
        "[REASONING: CRITIQUE]",
        "Content to evaluate:",
        f"  {preview}",
        "",
        "Evaluate the content across the following aspects:",
    ]
    for aspect in aspects:
        lines.append(f"  - {aspect}")
    lines += [
        "",
        "For each aspect:",
        "  - State what you observe",
        "  - Identify specific strengths",
        "  - Identify specific weaknesses or gaps",
        "  - Suggest a concrete improvement",
        "",
        "Output your reasoning tokens now. Be specific and direct. "
        "After completing all aspects, provide an overall assessment and priority recommendation.",
    ]
    return {"reasoning_instruction": "\n".join(lines)}


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_reasoning_tools() -> tuple[RegisteredTool, ...]:
    """Return all injectable reasoning tools as a stable tuple.

    These tools inject structured reasoning instructions into the agent's
    context window as tool results. The agent reads the instruction on its
    next turn and produces reasoning tokens in its assistant response.
    """
    return (
        RegisteredTool(
            definition=ToolDefinition(
                key=REASON_BRAINSTORM,
                name="brainstorm",
                description=(
                    "Inject a structured brainstorm instruction into the context window. "
                    "The agent will output reasoning tokens exploring a given number of "
                    "distinct ideas on the specified topic before selecting the strongest one. "
                    "Call this before create_script to generate and evaluate script angles."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "The subject to brainstorm ideas about.",
                        },
                        "count": {
                            "type": "integer",
                            "description": (
                                f"Number of ideas to generate ({_BRAINSTORM_COUNT_MIN}–{_BRAINSTORM_COUNT_MAX}). "
                                f"Defaults to {_BRAINSTORM_COUNT_DEFAULT}."
                            ),
                        },
                        "context": {
                            "type": "string",
                            "description": "Optional background information to inform the brainstorm.",
                        },
                        "constraints": {
                            "type": "string",
                            "description": "Optional constraints or requirements each idea must satisfy.",
                        },
                    },
                    "required": ["topic"],
                    "additionalProperties": False,
                },
            ),
            handler=brainstorm,
        ),
        RegisteredTool(
            definition=ToolDefinition(
                key=REASON_CHAIN_OF_THOUGHT,
                name="chain_of_thought",
                description=(
                    "Inject a step-by-step chain-of-thought reasoning instruction into the "
                    "context window. The agent will work through the specified task in explicit "
                    "numbered steps before reaching a conclusion. Use before complex decisions "
                    "or when a task requires careful sequential reasoning."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": "The task or question to reason through step by step.",
                        },
                        "steps": {
                            "type": "integer",
                            "description": (
                                f"Number of reasoning steps ({_COT_STEPS_MIN}–{_COT_STEPS_MAX}). "
                                f"Defaults to {_COT_STEPS_DEFAULT}."
                            ),
                        },
                        "context": {
                            "type": "string",
                            "description": "Optional background information to inform the reasoning.",
                        },
                    },
                    "required": ["task"],
                    "additionalProperties": False,
                },
            ),
            handler=chain_of_thought,
        ),
        RegisteredTool(
            definition=ToolDefinition(
                key=REASON_CRITIQUE,
                name="critique",
                description=(
                    "Inject a structured critique instruction into the context window. "
                    "The agent will evaluate the provided content across specified aspects "
                    "(correctness, clarity, completeness, improvements by default), "
                    "identify strengths and weaknesses, and produce a prioritized recommendation. "
                    "Use before finalizing scripts or avatar descriptions."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The text, plan, or output to critique.",
                        },
                        "aspects": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "Optional list of specific aspects to evaluate. "
                                "Defaults to: correctness, clarity, completeness, potential improvements."
                            ),
                        },
                    },
                    "required": ["content"],
                    "additionalProperties": False,
                },
            ),
            handler=critique,
        ),
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _require_string(arguments: ToolArguments, key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{key}' must be a non-empty string.")
    return value.strip()


def _optional_string(arguments: ToolArguments, key: str) -> str:
    value = arguments.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"'{key}' must be a string when provided.")
    return value.strip()


def _optional_int(arguments: ToolArguments, key: str, default: int) -> int:
    value = arguments.get(key)
    if value is None:
        return default
    if isinstance(value, bool):
        raise ValueError(f"'{key}' must be an integer, not a boolean.")
    if isinstance(value, int):
        return value
    raise ValueError(f"'{key}' must be an integer when provided.")


__all__ = [
    "REASON_BRAINSTORM",
    "REASON_CHAIN_OF_THOUGHT",
    "REASON_CRITIQUE",
    "brainstorm",
    "chain_of_thought",
    "create_reasoning_tools",
    "critique",
]
