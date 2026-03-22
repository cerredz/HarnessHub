"""Injectable reasoning tools for structured agent reasoning prompt injection."""

from __future__ import annotations

from harnessiq.shared.tools import (
    REASON_BRAINSTORM,
    REASON_BRAINSTORM_COUNT_DEFAULT,
    REASON_BRAINSTORM_COUNT_MAX,
    REASON_BRAINSTORM_COUNT_MIN,
    REASON_BRAINSTORM_COUNT_PRESETS,
    REASON_CHAIN_OF_THOUGHT,
    REASON_COT_STEPS_DEFAULT,
    REASON_COT_STEPS_MAX,
    REASON_COT_STEPS_MIN,
    REASON_CRITIQUE,
    RegisteredTool,
    ToolArguments,
    ToolDefinition,
)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def brainstorm(arguments: ToolArguments) -> dict[str, str]:
    """Inject a brainstorm reasoning instruction into the agent's context window."""
    topic = _require_string(arguments, "topic")
    count = _optional_brainstorm_count(arguments, "count", REASON_BRAINSTORM_COUNT_DEFAULT)
    if not (REASON_BRAINSTORM_COUNT_MIN <= count <= REASON_BRAINSTORM_COUNT_MAX):
        raise ValueError(
            f"'count' must be between {REASON_BRAINSTORM_COUNT_MIN} and "
            f"{REASON_BRAINSTORM_COUNT_MAX}, got {count}."
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
    steps = _optional_int(arguments, "steps", REASON_COT_STEPS_DEFAULT)
    if not (REASON_COT_STEPS_MIN <= steps <= REASON_COT_STEPS_MAX):
        raise ValueError(
            f"'steps' must be between {REASON_COT_STEPS_MIN} and "
            f"{REASON_COT_STEPS_MAX}, got {steps}."
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


def create_injectable_reasoning_tools() -> tuple[RegisteredTool, ...]:
    """Return the three injectable reasoning tools (brainstorm, chain_of_thought, critique).

    These tools inject structured reasoning instructions into the agent's
    context window as tool results. The agent reads the instruction on its
    next turn and produces reasoning tokens in its assistant response.

    Use ``create_reasoning_tools`` from ``harnessiq.tools.reasoning`` for the
    full 50-lens cognitive scaffolding toolkit.
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
                            "anyOf": [
                                {"type": "integer"},
                                {"type": "string", "enum": sorted(REASON_BRAINSTORM_COUNT_PRESETS)},
                            ],
                            "description": (
                                f"Number of ideas to generate "
                                f"({REASON_BRAINSTORM_COUNT_MIN}–{REASON_BRAINSTORM_COUNT_MAX}). "
                                f"Defaults to {REASON_BRAINSTORM_COUNT_DEFAULT}. "
                                "Also accepts the presets small, medium, or large."
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
                                f"Number of reasoning steps "
                                f"({REASON_COT_STEPS_MIN}–{REASON_COT_STEPS_MAX}). "
                                f"Defaults to {REASON_COT_STEPS_DEFAULT}."
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
                                "Defaults to: correctness, clarity, completeness, "
                                "potential improvements."
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


def _optional_brainstorm_count(arguments: ToolArguments, key: str, default: int) -> int:
    value = arguments.get(key)
    if value is None:
        return default
    if isinstance(value, bool):
        raise ValueError(f"'{key}' must be an integer or supported preset, not a boolean.")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in REASON_BRAINSTORM_COUNT_PRESETS:
            return REASON_BRAINSTORM_COUNT_PRESETS[normalized]
        raise ValueError(
            f"'count' preset must be one of {', '.join(sorted(REASON_BRAINSTORM_COUNT_PRESETS))}."
        )
    raise ValueError(f"'{key}' must be an integer or supported preset when provided.")


__all__ = [
    "brainstorm",
    "chain_of_thought",
    "create_injectable_reasoning_tools",
    "critique",
]
