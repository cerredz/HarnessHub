"""Small helpers for pytest-first evaluation suites."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from typing import Any


_MISSING = object()


def _stringify(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, sort_keys=True, default=str)
    except TypeError:
        return str(value)


def _lookup_value(payload: Any, name: str) -> Any:
    if isinstance(payload, Mapping):
        return payload.get(name, _MISSING)
    return getattr(payload, name, _MISSING)


def _resolve_value(payload: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        value = _lookup_value(payload, name)
        if value is _MISSING:
            continue
        if callable(value):
            return value()
        return value
    return default


def _coerce_count(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return len(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _ratio(actual: float | int | None, ideal: float | int | None) -> float | None:
    if actual is None or ideal in (None, 0):
        return None
    return float(actual) / float(ideal)


def get_run_value(run: Any, *names: str, default: Any = None) -> Any:
    """Return the first matching attribute or mapping key from ``run``."""
    return _resolve_value(run, *names, default=default)


def get_tool_call_count(run: Any) -> int | None:
    """Return the tool-call count from a generic run object or mapping."""
    explicit_count = _coerce_count(_resolve_value(run, "tool_call_count", default=None))
    if explicit_count is not None:
        return explicit_count
    return _coerce_count(_resolve_value(run, "tool_calls", default=None))


def get_step_count(run: Any) -> int | None:
    """Return the step count from a generic run object or mapping."""
    return _coerce_count(_resolve_value(run, "steps", "step_count", "cycles_completed", default=None))


def get_duration_seconds(run: Any) -> float | None:
    """Return the elapsed duration from a generic run object or mapping."""
    return _coerce_float(
        _resolve_value(run, "time", "duration_seconds", "elapsed_seconds", "latency_seconds", default=None)
    )


def uses_parallel_tool_calls(run: Any) -> bool | None:
    """Return whether the run reports parallel tool usage."""
    value = _resolve_value(run, "parallel_tool_calls", default=None)
    if value is None:
        return None
    return bool(value)


def score_efficiency(actual_run: Any, ideal_trajectory: Any) -> dict[str, float | None]:
    """Compare a run against a small ideal trajectory budget."""
    actual_steps = get_step_count(actual_run)
    actual_tool_calls = get_tool_call_count(actual_run)
    actual_time = get_duration_seconds(actual_run)

    ideal_steps = _coerce_count(_resolve_value(ideal_trajectory, "steps", "expected_steps", "expected_step_count"))
    ideal_tool_calls = _coerce_count(_resolve_value(ideal_trajectory, "tool_calls", "expected_tool_calls"))
    ideal_time = _coerce_float(
        _resolve_value(ideal_trajectory, "expected_time_seconds", "time_seconds", "duration_seconds")
    )

    return {
        "step_ratio": _ratio(actual_steps, ideal_steps),
        "tool_call_ratio": _ratio(actual_tool_calls, ideal_tool_calls),
        "latency_ratio": _ratio(actual_time, ideal_time),
    }


def build_llm_judge_prompt(
    agent_output: Any,
    expected: Any,
    *,
    task: str | None = None,
    rubric: str | None = None,
) -> str:
    """Build a simple yes-or-no judge prompt for semantic correctness."""
    lines = ["Did this output correctly accomplish the task?"]
    if task:
        lines.append(f"Task: {_stringify(task)}")
    if rubric:
        lines.append(f"Rubric: {_stringify(rubric)}")
    lines.append(f"Output: {_stringify(agent_output)}")
    lines.append(f"Expected: {_stringify(expected)}")
    lines.append("Reply yes or no.")
    return "\n".join(lines)


def _extract_judge_text(response: Any) -> str | None:
    if isinstance(response, bool):
        return "yes" if response else "no"
    if isinstance(response, str):
        return response
    if isinstance(response, Mapping):
        choices = response.get("choices")
        if isinstance(choices, Sequence) and choices:
            first = choices[0]
            if isinstance(first, Mapping):
                message = first.get("message")
                if isinstance(message, Mapping):
                    content = message.get("content")
                    if content is not None:
                        return str(content)
        content = response.get("content")
        if content is not None:
            return str(content)
        return None

    choices = getattr(response, "choices", None)
    if isinstance(choices, Sequence) and choices:
        first = choices[0]
        message = getattr(first, "message", None)
        content = getattr(message, "content", None)
        if content is not None:
            return str(content)
    content = getattr(response, "content", None)
    if content is not None:
        return str(content)
    return None


def llm_judge(
    agent_output: Any,
    expected: Any,
    *,
    judge: Callable[[str], Any],
    task: str | None = None,
    rubric: str | None = None,
) -> bool:
    """Run a caller-provided judge function against a simple semantic prompt."""
    prompt = build_llm_judge_prompt(agent_output, expected, task=task, rubric=rubric)
    response = judge(prompt)
    answer = (_extract_judge_text(response) or "").strip().lower()
    return answer in {"yes", "true", "pass", "passed"}


__all__ = [
    "build_llm_judge_prompt",
    "get_duration_seconds",
    "get_run_value",
    "get_step_count",
    "get_tool_call_count",
    "llm_judge",
    "score_efficiency",
    "uses_parallel_tool_calls",
]
