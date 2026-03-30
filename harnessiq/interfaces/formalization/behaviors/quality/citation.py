"""
===============================================================================
File: harnessiq/interfaces/formalization/behaviors/quality/citation.py

What this file does:
- Defines part of the abstract formalization interface surface used to describe
  harness behavior declaratively.
- Concrete citation-requirement behavior.

Use cases:
- Subclass or import these interfaces when building a new formalization layer
  family or behavior.

How to use it:
- Use the abstractions here to declare behavior, rules, and configuration in a
  form the runtime can later inspect or enforce.

Intent:
- Keep formalization contracts explicit and composable so harness rules are
  visible in code and docs.
===============================================================================
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from harnessiq.shared.agents import AgentParameterSection
from harnessiq.shared.tools import ToolCall, ToolResult

from .base import BaseQualityBehaviorLayer, QualityCriterionSpec


class CitationRequirementBehavior(BaseQualityBehaviorLayer):
    """Require citation fields in structured record outputs before gated tools appear."""

    def __init__(
        self,
        *,
        monitored_patterns: tuple[str, ...],
        required_fields: tuple[str, ...] = ("source_url", "publication_date"),
        record_argument_keys: tuple[str, ...] = ("records", "data"),
        blocked_until_cited: tuple[str, ...] = ("control.mark_complete",),
    ) -> None:
        self._monitored_patterns = tuple(monitored_patterns)
        self._required_fields = tuple(required_fields)
        self._record_argument_keys = tuple(record_argument_keys)
        self._blocked_patterns = tuple(blocked_until_cited)
        self._missing_records: list[dict[str, Any]] = []
        self._last_audited_tool: str | None = None

    def get_quality_criteria(self) -> tuple[QualityCriterionSpec, ...]:
        return (
            QualityCriterionSpec(
                criterion_id="CITATION_REQUIREMENTS",
                description=(
                    f"Structured records written through {self._monitored_patterns} must include "
                    f"{self._required_fields} before tools matching {self._blocked_patterns} are used."
                ),
            ),
        )

    def evaluate_criterion(
        self,
        criterion: QualityCriterionSpec,
        agent_state: dict[str, Any],
    ) -> tuple[bool, str]:
        del criterion
        missing_records = agent_state.get("missing_records", [])
        if not missing_records:
            return True, ""
        return False, "Structured output records are missing required citation fields."

    def _build_agent_state(self) -> dict[str, Any]:
        return {
            "required_fields": list(self._required_fields),
            "missing_records": list(self._missing_records),
            "last_audited_tool": self._last_audited_tool,
        }

    def filter_tool_keys(self, tool_keys: Sequence[str]) -> tuple[str, ...]:
        permitted: list[str] = []
        for tool_key in tool_keys:
            if self._missing_records and _is_tool_allowed(tool_key, self._blocked_patterns):
                continue
            permitted.append(tool_key)
        return tuple(permitted)

    def on_tool_call(self, tool_call: ToolCall) -> ToolCall:
        if not _is_tool_allowed(tool_call.tool_key, self._monitored_patterns):
            return tool_call
        self._last_audited_tool = tool_call.tool_key
        records = _extract_records(tool_call.arguments, self._record_argument_keys)
        self._missing_records = _find_missing_citations(records, self._required_fields)
        return tool_call

    def on_tool_result(self, result: ToolResult) -> ToolResult:
        return super().on_tool_result(result)

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        lines = [
            f"Required citation fields: {self._required_fields}",
            f"Monitored patterns: {self._monitored_patterns}",
            f"Blocked patterns while missing citations: {self._blocked_patterns}",
            f"Last audited tool: {self._last_audited_tool or 'none'}",
            f"Records missing citations: {len(self._missing_records)}",
        ]
        return (
            *super().get_parameter_sections(),
            AgentParameterSection(title=f"Behavior State: {self.layer_id}", content="\n".join(lines)),
        )


def _is_tool_allowed(tool_key: str, patterns: tuple[str, ...]) -> bool:
    from harnessiq.tools.hooks.defaults import is_tool_allowed

    return is_tool_allowed(tool_key, patterns)


def _extract_records(arguments: dict[str, Any], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    for key in keys:
        value = arguments.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested_records = value.get("records")
            if isinstance(nested_records, list):
                return [item for item in nested_records if isinstance(item, dict)]
    return []


def _find_missing_citations(
    records: list[dict[str, Any]],
    required_fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    missing: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        missing_fields = [
            field
            for field in required_fields
            if not str(record.get(field, "")).strip()
        ]
        if missing_fields:
            missing.append({"index": index, "missing_fields": missing_fields})
    return missing
