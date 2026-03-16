"""Core injectable reasoning tools: brainstorm, chain_of_thought, and critique."""

from __future__ import annotations

from harnessiq.shared.tools import (
    REASON_BRAINSTORM,
    REASON_CHAIN_OF_THOUGHT,
    REASON_CRITIQUE,
    RegisteredTool,
    ToolArguments,
    ToolDefinition,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BRAINSTORM_COUNT_MIN = 5
_BRAINSTORM_COUNT_MAX = 30
_BRAINSTORM_COUNT_DEFAULT = 10

# String presets for the brainstorm count parameter.  Each key resolves to a
# concrete idea count so callers can express intent without knowing the exact
# numeric boundary.
_BRAINSTORM_COUNT_PRESETS: dict[str, int] = {
    "small": 5,
    "medium": 15,
    "large": 30,
}

_COT_STEPS_MIN = 3
_COT_STEPS_MAX = 10
_COT_STEPS_DEFAULT = 5


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def brainstorm(arguments: ToolArguments) -> dict[str, str]:
    """Inject a brainstorm reasoning instruction into the agent's context window."""
    topic = _require_string(arguments, "topic")
    count = _resolve_brainstorm_count(arguments)
    context = _optional_string(arguments, "context")
    constraints = _optional_string(arguments, "constraints")

    parts = [
        "[REASONING: BRAINSTORM]",
        (
            f"You are beginning a structured brainstorm on the following topic: {topic}. "
            f"Your goal is to generate {count} distinct, well-considered ideas before "
            "committing to any single direction."
        ),
    ]
    if context:
        parts.append(f"Your brainstorm should be grounded in the following context: {context}.")
    if constraints:
        parts.append(
            f"Every idea you generate must satisfy the following constraints: {constraints}."
        )
    parts.append(
        f"For each of the {count} ideas, provide a concise title, a one-sentence rationale "
        "explaining why it could work, and an estimated impact level (low, medium, or high). "
        "Think through each idea independently and carefully before moving to the next — "
        "do not converge on a favourite prematurely. After generating all "
        f"{count} ideas, identify the single strongest one and explain your selection "
        "reasoning in full."
    )
    return {"reasoning_instruction": "\n\n".join(parts)}


def chain_of_thought(arguments: ToolArguments) -> dict[str, str]:
    """Inject a chain-of-thought reasoning instruction into the agent's context window."""
    task = _require_string(arguments, "task")
    steps = _optional_int(arguments, "steps", _COT_STEPS_DEFAULT)
    if not (_COT_STEPS_MIN <= steps <= _COT_STEPS_MAX):
        raise ValueError(
            f"'steps' must be between {_COT_STEPS_MIN} and {_COT_STEPS_MAX}, got {steps}."
        )
    context = _optional_string(arguments, "context")

    parts = [
        "[REASONING: CHAIN OF THOUGHT]",
        (
            f"You are beginning a structured chain-of-thought analysis of the following task: "
            f"{task}. Work through this problem in exactly {steps} sequential, explicitly "
            "numbered steps."
        ),
    ]
    if context:
        parts.append(f"The following context should inform your reasoning: {context}.")
    parts.append(
        f"For each of the {steps} steps, state what specific aspect of the problem you are "
        "reasoning about in that step, develop your reasoning fully before drawing any "
        "conclusion, and then state a clear partial conclusion before proceeding to the next "
        "step. Do not skip steps, combine steps, or jump to the final answer ahead of time. "
        f"After completing all {steps} steps, state your final integrated conclusion."
    )
    return {"reasoning_instruction": "\n\n".join(parts)}


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

    # Truncate content preview to keep the instruction concise.
    preview = content if len(content) <= 300 else content[:297] + "..."

    aspects_prose = ", ".join(aspects[:-1]) + (f", and {aspects[-1]}" if len(aspects) > 1 else aspects[0])

    parts = [
        "[REASONING: CRITIQUE]",
        f"You are conducting a structured critique of the following content: {preview}",
        (
            f"Evaluate the content across these specific aspects: {aspects_prose}. "
            "For each aspect, describe what you observe in concrete and specific terms, "
            "identify its strengths, surface any weaknesses or gaps, and suggest one "
            "actionable improvement. Avoid vague generalizations — be precise about what "
            "is working and what is not. After completing all aspects, provide an overall "
            "assessment and identify the single highest-priority improvement."
        ),
    ]
    return {"reasoning_instruction": "\n\n".join(parts)}


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_reasoning_tools() -> tuple[RegisteredTool, ...]:
    """Return the three core injectable reasoning tools as a stable tuple.

    These tools inject structured reasoning instructions into the agent's
    context window as tool results. The agent reads the instruction on its
    next turn and produces reasoning in its assistant response before taking
    any action.  They are opt-in: add them to a ToolRegistry alongside other
    agent tools rather than including them in BUILTIN_TOOLS.
    """
    return (
        RegisteredTool(
            definition=ToolDefinition(
                key=REASON_BRAINSTORM,
                name="brainstorm",
                description=(
                    "Use this tool to begin a structured brainstorm before making any creative "
                    "or strategic decision. It injects a targeted reasoning instruction into the "
                    "context window: the model will generate a specified number of distinct ideas "
                    "on the given topic, evaluate each one for rationale and estimated impact, "
                    "and then identify the strongest candidate before proceeding. This is the "
                    "mandatory first step in any content creation or strategy pipeline — call it "
                    "before create_script or any other decision-dependent tool to ensure the "
                    "solution space has been explored before committing to a direction. The count "
                    "parameter accepts an integer from 5 to 30 or one of three preset strings: "
                    "\"small\" (5 ideas), \"medium\" (15 ideas), or \"large\" (30 ideas). An "
                    "optional context string grounds the brainstorm in relevant background "
                    "information, and an optional constraints string narrows the solution space "
                    "to ideas that satisfy specific requirements."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "The subject or question to brainstorm ideas about.",
                        },
                        "count": {
                            "anyOf": [
                                {"type": "integer", "minimum": 5, "maximum": 30},
                                {"type": "string", "enum": ["small", "medium", "large"]},
                            ],
                            "description": (
                                'Number of ideas to generate. Accepts an integer (5–30) or a '
                                'preset string: "small" (5), "medium" (15), or "large" (30). '
                                f"Defaults to {_BRAINSTORM_COUNT_DEFAULT}."
                            ),
                        },
                        "context": {
                            "type": "string",
                            "description": (
                                "Optional background information that should inform the brainstorm, "
                                "such as audience details, product context, or prior research."
                            ),
                        },
                        "constraints": {
                            "type": "string",
                            "description": (
                                "Optional requirements or restrictions that every generated idea "
                                "must satisfy, such as format constraints, length limits, or "
                                "topic boundaries."
                            ),
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
                    "Use this tool when a task requires careful sequential reasoning before "
                    "arriving at a conclusion. It injects a structured chain-of-thought "
                    "instruction into the context window: the model will work through the "
                    "specified task in a fixed number of explicit, numbered steps — each step "
                    "stating its focus, developing its reasoning fully, and reaching a partial "
                    "conclusion before advancing to the next. This prevents premature convergence "
                    "and produces a transparent decision trail that can be inspected or critiqued. "
                    "Use it before any complex creative decision, evaluation, or multi-factor "
                    "analysis that should not be handled in a single unstructured pass. The steps "
                    "parameter controls reasoning depth and accepts an integer from 3 to 10, "
                    "defaulting to 5. An optional context string can be supplied to anchor the "
                    "reasoning in relevant background information."
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
                                f"Defaults to {_COT_STEPS_DEFAULT}. Use more steps for complex "
                                "multi-factor decisions and fewer for simpler evaluations."
                            ),
                        },
                        "context": {
                            "type": "string",
                            "description": (
                                "Optional background information that should inform the reasoning, "
                                "such as audience context, prior brainstorm results, or constraints."
                            ),
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
                    "Use this tool to evaluate an artifact — a script, plan, description, or "
                    "any other piece of content — before finalizing it. It injects a structured "
                    "critique instruction into the context window: the model will analyze the "
                    "provided content across a set of evaluation aspects, identifying concrete "
                    "strengths and weaknesses for each, and producing a prioritized improvement "
                    "recommendation. The default evaluation aspects are correctness, clarity, "
                    "completeness, and potential improvements, but any domain-specific aspects "
                    "can be supplied via the aspects list. Call this after create_script or "
                    "create_avatar_description to surface issues before they propagate into "
                    "downstream steps such as create_video."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": (
                                "The text, plan, script, or other output to evaluate. "
                                "Content longer than 300 characters will be previewed and "
                                "truncated in the injected instruction."
                            ),
                        },
                        "aspects": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "Optional list of specific evaluation aspects to assess. "
                                "Defaults to: correctness, clarity, completeness, and potential "
                                "improvements. Supply domain-specific aspects such as \"tone\", "
                                "\"hook strength\", or \"call-to-action clarity\" when relevant."
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


def _resolve_brainstorm_count(arguments: ToolArguments) -> int:
    """Resolve the brainstorm count from an int, a preset string, or the default."""
    raw = arguments.get("count")
    if raw is None:
        return _BRAINSTORM_COUNT_DEFAULT
    if isinstance(raw, bool):
        raise ValueError("'count' must be an integer or preset string, not a boolean.")
    if isinstance(raw, str):
        if raw not in _BRAINSTORM_COUNT_PRESETS:
            valid = ", ".join(f'"{k}"' for k in _BRAINSTORM_COUNT_PRESETS)
            raise ValueError(
                f"'count' preset must be one of {valid}, got '{raw}'."
            )
        return _BRAINSTORM_COUNT_PRESETS[raw]
    if isinstance(raw, int):
        if not (_BRAINSTORM_COUNT_MIN <= raw <= _BRAINSTORM_COUNT_MAX):
            raise ValueError(
                f"'count' must be between {_BRAINSTORM_COUNT_MIN} and "
                f"{_BRAINSTORM_COUNT_MAX}, got {raw}."
            )
        return raw
    raise ValueError("'count' must be an integer or preset string when provided.")


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
    "brainstorm",
    "chain_of_thought",
    "create_reasoning_tools",
    "critique",
]
