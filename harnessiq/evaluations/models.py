"""Core data models for the evaluation scaffolding layer."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any


def _validate_non_negative(value: float | int | None, *, field_name: str) -> None:
    if value is not None and value < 0:
        raise ValueError(f"{field_name} must be non-negative.")


@dataclass(frozen=True, slots=True)
class EvaluationToolCall:
    """Normalized representation of one tool invocation within an eval trace."""

    key: str
    arguments: dict[str, Any] = field(default_factory=dict)
    output: Any = None
    duration_seconds: float | None = None

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError("EvaluationToolCall key must not be blank.")
        object.__setattr__(self, "arguments", dict(self.arguments))
        _validate_non_negative(self.duration_seconds, field_name="duration_seconds")

    @classmethod
    def from_value(cls, value: EvaluationToolCall | str | Mapping[str, Any]) -> EvaluationToolCall:
        """Coerce a simple string or mapping into a normalized tool-call payload."""
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            return cls(key=value)
        if not isinstance(value, Mapping):
            raise TypeError("EvaluationToolCall values must be strings, mappings, or EvaluationToolCall instances.")

        raw_key = value.get("key", value.get("tool_key"))
        if not isinstance(raw_key, str):
            raise TypeError("EvaluationToolCall mappings must provide a string 'key' or 'tool_key'.")

        raw_arguments = value.get("arguments", {})
        if not isinstance(raw_arguments, Mapping):
            raise TypeError("EvaluationToolCall arguments must be a mapping when provided.")

        raw_duration = value.get("duration_seconds")
        duration_seconds = float(raw_duration) if raw_duration is not None else None

        return cls(
            key=raw_key,
            arguments=dict(raw_arguments),
            output=value.get("output"),
            duration_seconds=duration_seconds,
        )


@dataclass(frozen=True, slots=True)
class EvaluationContext:
    """Normalized input payload passed to one or more evaluation checks."""

    task: str = ""
    final_output: Any = None
    tool_calls: tuple[EvaluationToolCall, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    step_count: int | None = None
    duration_seconds: float | None = None
    cost_usd: float | None = None
    expected_tool_calls: int | None = None
    expected_step_count: int | None = None
    expected_duration_seconds: float | None = None
    expected_cost_usd: float | None = None

    def __post_init__(self) -> None:
        normalized_calls = tuple(EvaluationToolCall.from_value(call) for call in self.tool_calls)
        object.__setattr__(self, "tool_calls", normalized_calls)
        object.__setattr__(self, "metadata", dict(self.metadata))

        _validate_non_negative(self.step_count, field_name="step_count")
        _validate_non_negative(self.duration_seconds, field_name="duration_seconds")
        _validate_non_negative(self.cost_usd, field_name="cost_usd")
        _validate_non_negative(self.expected_tool_calls, field_name="expected_tool_calls")
        _validate_non_negative(self.expected_step_count, field_name="expected_step_count")
        _validate_non_negative(self.expected_duration_seconds, field_name="expected_duration_seconds")
        _validate_non_negative(self.expected_cost_usd, field_name="expected_cost_usd")

        if self.step_count is None:
            object.__setattr__(self, "step_count", len(normalized_calls))

    @property
    def tool_keys(self) -> tuple[str, ...]:
        """Return the ordered sequence of invoked tool keys."""
        return tuple(call.key for call in self.tool_calls)

    def tool_call_count(self, tool_key: str | None = None) -> int:
        """Return the total or per-tool call count."""
        if tool_key is None:
            return len(self.tool_calls)
        return sum(1 for call in self.tool_calls if call.key == tool_key)

    def has_tool_call(self, tool_key: str) -> bool:
        """Return whether the trace includes at least one call to ``tool_key``."""
        return any(call.key == tool_key for call in self.tool_calls)


@dataclass(frozen=True, slots=True)
class EvaluationCheckResult:
    """Structured outcome from a single evaluation helper."""

    name: str
    passed: bool
    message: str
    expected: Any = None
    actual: Any = None
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("EvaluationCheckResult name must not be blank.")
        object.__setattr__(self, "details", dict(self.details))


EvaluationCheck = Callable[[EvaluationContext], EvaluationCheckResult]


__all__ = [
    "EvaluationCheck",
    "EvaluationCheckResult",
    "EvaluationContext",
    "EvaluationToolCall",
]
