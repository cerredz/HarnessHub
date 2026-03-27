"""Reusable, pytest-friendly evaluation helper factories."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from .metrics import solve_rate
from .models import EvaluationCheck, EvaluationCheckResult, EvaluationContext


def _render_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, sort_keys=True, default=str)
    except TypeError:
        return str(value)


def _lookup_path(payload: Any, dotted_path: str) -> tuple[bool, Any]:
    current = payload
    for segment in dotted_path.split("."):
        if not isinstance(current, Mapping) or segment not in current:
            return False, None
        current = current[segment]
    return True, current


def _check_result(
    name: str,
    passed: bool,
    message: str,
    *,
    expected: Any = None,
    actual: Any = None,
    details: Mapping[str, Any] | None = None,
) -> EvaluationCheckResult:
    return EvaluationCheckResult(
        name=name,
        passed=passed,
        message=message,
        expected=expected,
        actual=actual,
        details=dict(details or {}),
    )


def final_output_exists(*, name: str = "final_output_exists") -> EvaluationCheck:
    """Require the evaluation context to include a non-empty final output."""

    def check(context: EvaluationContext) -> EvaluationCheckResult:
        output = context.final_output
        passed = output is not None and output != "" and output != [] and output != {}
        message = "Final output exists." if passed else "Final output is missing."
        return _check_result(name, passed, message, expected="non-empty final output", actual=output)

    return check


def output_contains(fragment: str, *, case_sensitive: bool = False, name: str | None = None) -> EvaluationCheck:
    """Require the rendered final output to contain one substring."""

    check_name = name or "output_contains"

    def check(context: EvaluationContext) -> EvaluationCheckResult:
        haystack = _render_value(context.final_output)
        candidate = haystack if case_sensitive else haystack.lower()
        needle = fragment if case_sensitive else fragment.lower()
        passed = needle in candidate
        message = f"Final output contains {fragment!r}." if passed else f"Final output does not contain {fragment!r}."
        return _check_result(check_name, passed, message, expected=fragment, actual=haystack)

    return check


def output_contains_all(
    fragments: Sequence[str],
    *,
    case_sensitive: bool = False,
    name: str | None = None,
) -> EvaluationCheck:
    """Require the rendered final output to contain every requested fragment."""

    check_name = name or "output_contains_all"
    expected_fragments = tuple(fragments)

    def check(context: EvaluationContext) -> EvaluationCheckResult:
        haystack = _render_value(context.final_output)
        candidate = haystack if case_sensitive else haystack.lower()
        missing = [
            fragment
            for fragment in expected_fragments
            if (fragment if case_sensitive else fragment.lower()) not in candidate
        ]
        passed = not missing
        message = "Final output contains all requested fragments." if passed else f"Missing fragments: {missing!r}."
        return _check_result(
            check_name,
            passed,
            message,
            expected=list(expected_fragments),
            actual=haystack,
            details={"missing": missing},
        )

    return check


def output_matches_regex(pattern: str, *, flags: int = 0, name: str | None = None) -> EvaluationCheck:
    """Require the rendered final output to match a regex."""

    check_name = name or "output_matches_regex"
    compiled = re.compile(pattern, flags)

    def check(context: EvaluationContext) -> EvaluationCheckResult:
        haystack = _render_value(context.final_output)
        passed = compiled.search(haystack) is not None
        message = f"Final output matches {pattern!r}." if passed else f"Final output does not match {pattern!r}."
        return _check_result(check_name, passed, message, expected=pattern, actual=haystack)

    return check


def output_field_equals(field_path: str, expected: Any, *, name: str | None = None) -> EvaluationCheck:
    """Require a dotted field path in the final output mapping to equal ``expected``."""

    check_name = name or "output_field_equals"

    def check(context: EvaluationContext) -> EvaluationCheckResult:
        found, actual = _lookup_path(context.final_output, field_path)
        passed = found and actual == expected
        if not found:
            message = f"Final output field {field_path!r} is missing."
        elif passed:
            message = f"Final output field {field_path!r} matches."
        else:
            message = f"Final output field {field_path!r} does not match."
        return _check_result(
            check_name,
            passed,
            message,
            expected=expected,
            actual=actual,
            details={"field_path": field_path, "found": found},
        )

    return check


def metadata_has_keys(*keys: str, name: str | None = None) -> EvaluationCheck:
    """Require all requested metadata keys or dotted metadata paths to exist."""

    check_name = name or "metadata_has_keys"
    required_keys = tuple(keys)

    def check(context: EvaluationContext) -> EvaluationCheckResult:
        missing = [key for key in required_keys if not _lookup_path(context.metadata, key)[0]]
        passed = not missing
        message = "All required metadata keys are present." if passed else f"Missing metadata keys: {missing!r}."
        return _check_result(
            check_name,
            passed,
            message,
            expected=list(required_keys),
            actual=context.metadata,
            details={"missing": missing},
        )

    return check


def tool_called(tool_key: str, *, name: str | None = None) -> EvaluationCheck:
    """Require at least one call to a specific tool."""

    check_name = name or "tool_called"

    def check(context: EvaluationContext) -> EvaluationCheckResult:
        passed = context.has_tool_call(tool_key)
        message = f"Tool {tool_key!r} was called." if passed else f"Tool {tool_key!r} was not called."
        return _check_result(check_name, passed, message, expected=tool_key, actual=context.tool_keys)

    return check


def tool_not_called(tool_key: str, *, name: str | None = None) -> EvaluationCheck:
    """Require that a specific tool never appears in the trace."""

    check_name = name or "tool_not_called"

    def check(context: EvaluationContext) -> EvaluationCheckResult:
        passed = not context.has_tool_call(tool_key)
        message = f"Tool {tool_key!r} was not called." if passed else f"Tool {tool_key!r} was called unexpectedly."
        return _check_result(check_name, passed, message, expected=f"no calls to {tool_key}", actual=context.tool_keys)

    return check


def tool_called_exactly(tool_key: str, count: int, *, name: str | None = None) -> EvaluationCheck:
    """Require a tool to be called exactly ``count`` times."""

    check_name = name or "tool_called_exactly"

    def check(context: EvaluationContext) -> EvaluationCheckResult:
        actual = context.tool_call_count(tool_key)
        passed = actual == count
        message = (
            f"Tool {tool_key!r} was called exactly {count} times."
            if passed
            else f"Tool {tool_key!r} was called {actual} times instead of {count}."
        )
        return _check_result(check_name, passed, message, expected=count, actual=actual, details={"tool_key": tool_key})

    return check


def tool_called_at_least(tool_key: str, minimum: int, *, name: str | None = None) -> EvaluationCheck:
    """Require a tool to be called at least ``minimum`` times."""

    check_name = name or "tool_called_at_least"

    def check(context: EvaluationContext) -> EvaluationCheckResult:
        actual = context.tool_call_count(tool_key)
        passed = actual >= minimum
        message = (
            f"Tool {tool_key!r} met the minimum call count."
            if passed
            else f"Tool {tool_key!r} was called {actual} times; expected at least {minimum}."
        )
        return _check_result(check_name, passed, message, expected=minimum, actual=actual, details={"tool_key": tool_key})

    return check


def tool_call_count_at_most(maximum: int, *, name: str | None = None) -> EvaluationCheck:
    """Require the total tool-call count to stay within a ceiling."""

    check_name = name or "tool_call_count_at_most"

    def check(context: EvaluationContext) -> EvaluationCheckResult:
        actual = context.tool_call_count()
        passed = actual <= maximum
        message = (
            f"Tool-call count stayed within {maximum}."
            if passed
            else f"Tool-call count was {actual}; expected at most {maximum}."
        )
        return _check_result(check_name, passed, message, expected=maximum, actual=actual)

    return check


def tools_called_in_order(*tool_keys: str, name: str | None = None) -> EvaluationCheck:
    """Require the listed tool keys to appear in order within the trace."""

    check_name = name or "tools_called_in_order"
    expected_order = tuple(tool_keys)

    def check(context: EvaluationContext) -> EvaluationCheckResult:
        observed = list(context.tool_keys)
        index = 0
        for expected_key in expected_order:
            try:
                index = observed.index(expected_key, index) + 1
            except ValueError:
                return _check_result(
                    check_name,
                    False,
                    f"Tool order {expected_order!r} was not observed.",
                    expected=list(expected_order),
                    actual=observed,
                )
        return _check_result(
            check_name,
            True,
            "Requested tool order was observed.",
            expected=list(expected_order),
            actual=observed,
        )

    return check


def step_count_at_most(maximum: int, *, name: str | None = None) -> EvaluationCheck:
    """Require the run to complete within a step budget."""

    check_name = name or "step_count_at_most"

    def check(context: EvaluationContext) -> EvaluationCheckResult:
        actual = context.step_count
        passed = actual is not None and actual <= maximum
        message = f"Step count stayed within {maximum}." if passed else f"Step count was {actual}; expected at most {maximum}."
        return _check_result(check_name, passed, message, expected=maximum, actual=actual)

    return check


def duration_at_most(maximum_seconds: float, *, name: str | None = None) -> EvaluationCheck:
    """Require the run duration to stay within a ceiling."""

    check_name = name or "duration_at_most"

    def check(context: EvaluationContext) -> EvaluationCheckResult:
        actual = context.duration_seconds
        passed = actual is not None and actual <= maximum_seconds
        message = (
            f"Duration stayed within {maximum_seconds} seconds."
            if passed
            else f"Duration was {actual}; expected at most {maximum_seconds} seconds."
        )
        return _check_result(check_name, passed, message, expected=maximum_seconds, actual=actual)

    return check


def solve_rate_at_least(minimum: float, *, name: str | None = None) -> EvaluationCheck:
    """Require the run's solve rate to meet a minimum threshold."""

    check_name = name or "solve_rate_at_least"

    def check(context: EvaluationContext) -> EvaluationCheckResult:
        actual = solve_rate(context)
        passed = actual is not None and actual >= minimum
        message = f"Solve rate met the threshold {minimum}." if passed else f"Solve rate was {actual}; expected at least {minimum}."
        return _check_result(check_name, passed, message, expected=minimum, actual=actual)

    return check


__all__ = [
    "duration_at_most",
    "final_output_exists",
    "metadata_has_keys",
    "output_contains",
    "output_contains_all",
    "output_field_equals",
    "output_matches_regex",
    "solve_rate_at_least",
    "step_count_at_most",
    "tool_call_count_at_most",
    "tool_called",
    "tool_called_at_least",
    "tool_called_exactly",
    "tool_not_called",
    "tools_called_in_order",
]
