"""Concrete tool-call budget behavior."""

from __future__ import annotations

from collections.abc import Mapping

from harnessiq.shared.agents import AgentParameterSection
from harnessiq.tools.hooks.defaults import is_tool_allowed

from .base import BaseToolBehaviorLayer, ToolConstraintSpec


def _constraint_id(prefix: str, pattern: str) -> str:
    normalized = pattern.upper().replace("*", "X").replace(".", "_")
    return f"{prefix}-{normalized}"


class ToolCallLimitBehavior(BaseToolBehaviorLayer):
    """Limit how many times matching tools may be called per context reset."""

    def __init__(self, limits: Mapping[str, int]) -> None:
        self._limits = {
            str(pattern): int(limit)
            for pattern, limit in limits.items()
            if str(pattern).strip()
        }
        self._call_counts: dict[str, int] = {}

    def get_tool_constraints(self) -> tuple[ToolConstraintSpec, ...]:
        return tuple(
            ToolConstraintSpec(
                constraint_id=_constraint_id("TOOL_LIMIT", pattern),
                tool_patterns=(pattern,),
                description=(
                    f"Tools matching '{pattern}' may be called at most {limit} times "
                    "per context reset. The tool is hidden after the limit is reached."
                ),
                limit=limit,
            )
            for pattern, limit in self._limits.items()
        )

    def is_tool_call_permitted(
        self,
        tool_key: str,
        reset_count: int,
        cycle_index: int,
    ) -> tuple[bool, str]:
        del reset_count, cycle_index
        for pattern, limit in self._limits.items():
            if not is_tool_allowed(tool_key, (pattern,)):
                continue
            if self._call_counts.get(tool_key, 0) >= limit:
                return False, f"limit {limit} reached for '{pattern}'"
        return True, ""

    def record_tool_call(self, tool_key: str) -> None:
        self._call_counts[tool_key] = self._call_counts.get(tool_key, 0) + 1

    def on_post_reset(self) -> None:
        super().on_post_reset()
        self._call_counts.clear()

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        lines = ["Tool call budget per context reset:"]
        for pattern, limit in self._limits.items():
            used = sum(
                count
                for tool_key, count in self._call_counts.items()
                if is_tool_allowed(tool_key, (pattern,))
            )
            lines.append(f"- {pattern}: {used}/{limit} used")
        return (
            *super().get_parameter_sections(),
            AgentParameterSection(
                title=f"Behavior State: {self.layer_id}",
                content="\n".join(lines),
            ),
        )
