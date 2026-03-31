"""
===============================================================================
File: harnessiq/formalization/criteria/criterion.py

What this file does:
- Defines StopCriterion, the abstract base for a single success condition.
- Provides four built-in concrete criterion types:
    MetricCriterion   — checks a metric value against a threshold
    ArtifactCriterion — checks whether an output artifact has been written
    FileCriterion     — checks whether a file exists and meets size constraints
    CallableCriterion — delegates to an arbitrary Python callable

Use cases:
- Compose criterion instances and pass to CriteriaExpression (AndCriteria,
  OrCriteria, SingleCriterion), then wrap in StopCriteriaLayer.

Intent:
- Keep individual success conditions small, named, and independently testable.
  Each criterion reports both a boolean pass/fail and a human-readable progress
  string so the model can understand exactly what it still needs to do.
===============================================================================
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from harnessiq.formalization.artifacts.output_layer import OutputArtifactLayer
    from harnessiq.formalization.metrics.layer import MetricsLayer


class StopCriterion(ABC):
    """Abstract base for one success condition.

    A criterion is evaluated at every completion attempt. If satisfied, the
    completion is allowed (subject to other criteria). If not, completion is
    blocked and the error_message/progress pair is injected into the transcript
    so the model understands what it still needs to do.
    """

    @property
    @abstractmethod
    def criterion_id(self) -> str:
        """Stable identifier. Shown in describe() and in error messages."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Plain language description of what must be true to stop."""

    @abstractmethod
    def is_satisfied(self) -> bool:
        """Return True if this criterion currently passes."""

    @abstractmethod
    def progress(self) -> str:
        """Return a human-readable string describing current progress.

        Shown to the model in the error injection when the criterion is not met.
        Example: "git_commits: 47 / 100 required"
        """


# ── Built-in concrete criterion types ────────────────────────────────────────


@dataclass
class MetricCriterion(StopCriterion):
    """Criterion: a metric must satisfy a threshold before the agent can stop.

    Example::

        MetricCriterion(
            metric_name="git_commits",
            operator=">=",
            target=100,
            metrics_layer=my_metrics_layer,
        )
    """

    metric_name: str
    operator: str  # ">=", ">", "==", "<=", "<", "!="
    target: Any
    metrics_layer: MetricsLayer

    @property
    def criterion_id(self) -> str:
        return f"METRIC-{self.metric_name.upper()}-{self.operator}-{self.target}"

    @property
    def description(self) -> str:
        return (
            f"Metric '{self.metric_name}' must be {self.operator} {self.target} "
            f"before the agent is allowed to stop."
        )

    def is_satisfied(self) -> bool:
        value = self.metrics_layer.get_value(self.metric_name)
        if value is None:
            return False
        ops = {
            ">=": lambda a, b: a >= b,
            ">": lambda a, b: a > b,
            "==": lambda a, b: a == b,
            "<=": lambda a, b: a <= b,
            "<": lambda a, b: a < b,
            "!=": lambda a, b: a != b,
        }
        op = ops.get(self.operator)
        return op is not None and op(value, self.target)

    def progress(self) -> str:
        value = self.metrics_layer.get_value(self.metric_name)
        return (
            f"'{self.metric_name}': current={value}, "
            f"required {self.operator} {self.target}"
        )


@dataclass
class ArtifactCriterion(StopCriterion):
    """Criterion: a declared output artifact must have been written.

    Example::

        ArtifactCriterion(
            artifact_name="final_report",
            output_layer=my_output_layer,
        )
    """

    artifact_name: str
    output_layer: OutputArtifactLayer
    description_override: str = ""

    @property
    def criterion_id(self) -> str:
        return f"ARTIFACT-{self.artifact_name.upper()}-WRITTEN"

    @property
    def description(self) -> str:
        return self.description_override or (
            f"Output artifact '{self.artifact_name}' must be written "
            f"before the agent is allowed to stop."
        )

    def is_satisfied(self) -> bool:
        return self.artifact_name in self.output_layer._written

    def progress(self) -> str:
        written = self.artifact_name in self.output_layer._written
        status = "written \u2713" if written else "not yet written \u2717"
        return f"'{self.artifact_name}': {status}"


@dataclass
class FileCriterion(StopCriterion):
    """Criterion: a file must exist and optionally meet size constraints.

    Example::

        FileCriterion(
            _criterion_id="OUTPUT-FILE-LARGE-ENOUGH",
            _description="output.py must be at least 10,000 lines",
            path="{memory_path}/outputs/output.py",
            min_lines=10_000,
        )
    """

    _criterion_id: str
    _description: str
    path: str  # supports {memory_path} template substitution
    min_lines: int | None = None
    min_bytes: int | None = None
    must_exist: bool = True
    _memory_path: str = ""

    @property
    def criterion_id(self) -> str:
        return self._criterion_id

    @property
    def description(self) -> str:
        return self._description

    def bind_memory_path(self, memory_path: str) -> None:
        """Set the memory path used to resolve {memory_path} in the path template."""
        self._memory_path = memory_path

    def _resolved_path(self):
        from pathlib import Path
        raw = self.path.replace("{memory_path}", self._memory_path)
        return Path(raw)

    def is_satisfied(self) -> bool:
        p = self._resolved_path()
        if not p.exists():
            return not self.must_exist
        if self.min_bytes is not None and p.stat().st_size < self.min_bytes:
            return False
        if self.min_lines is not None:
            lines = p.read_text(encoding="utf-8", errors="replace").count("\n")
            if lines < self.min_lines:
                return False
        return True

    def progress(self) -> str:
        p = self._resolved_path()
        if not p.exists():
            return f"File '{p.name}': does not exist yet"
        parts = [f"File '{p.name}': exists ({p.stat().st_size:,} bytes)"]
        if self.min_lines is not None:
            lines = p.read_text(encoding="utf-8", errors="replace").count("\n")
            parts.append(f"{lines:,} / {self.min_lines:,} lines")
        if self.min_bytes is not None:
            parts.append(f"{p.stat().st_size:,} / {self.min_bytes:,} bytes")
        return ", ".join(parts)


@dataclass
class CallableCriterion(StopCriterion):
    """Criterion: an arbitrary Python callable decides satisfaction.

    The callable receives no arguments and returns ``(is_satisfied: bool, progress: str)``.
    Use this for criteria that don't fit the other types.

    Example::

        CallableCriterion(
            _criterion_id="CUSTOM-QUALITY-GATE",
            _description="Custom quality check must pass.",
            check=lambda: (validate_output_quality(), "quality score: X/100"),
        )
    """

    _criterion_id: str
    _description: str
    check: Any  # Callable[[], tuple[bool, str]]

    @property
    def criterion_id(self) -> str:
        return self._criterion_id

    @property
    def description(self) -> str:
        return self._description

    def is_satisfied(self) -> bool:
        satisfied, _ = self.check()
        return satisfied

    def progress(self) -> str:
        _, prog = self.check()
        return prog
