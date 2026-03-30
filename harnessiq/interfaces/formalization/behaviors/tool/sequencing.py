"""
===============================================================================
File: harnessiq/interfaces/formalization/behaviors/tool/sequencing.py

What this file does:
- Defines part of the abstract formalization interface surface used to describe
  harness behavior declaratively.
- Concrete prerequisite-ordering behavior.

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

from collections.abc import Mapping, Sequence

from harnessiq.shared.agents import AgentParameterSection

from .base import BaseToolBehaviorLayer, ToolConstraintSpec
from .limit import _constraint_id


class ToolSequencingBehavior(BaseToolBehaviorLayer):
    """Require prerequisite tool families before target tool families appear."""

    def __init__(self, prerequisites: Mapping[str, Sequence[str]]) -> None:
        self._prerequisites = {
            str(target_pattern): tuple(str(pattern) for pattern in patterns if str(pattern).strip())
            for target_pattern, patterns in prerequisites.items()
            if str(target_pattern).strip()
        }
        self._satisfied_targets: set[str] = set()

    def get_tool_constraints(self) -> tuple[ToolConstraintSpec, ...]:
        return tuple(
            ToolConstraintSpec(
                constraint_id=_constraint_id("TOOL_SEQUENCE", target_pattern),
                tool_patterns=(target_pattern,),
                prerequisite_patterns=prerequisite_patterns,
                description=(
                    f"Tools matching '{target_pattern}' remain hidden until a tool matching "
                    f"{prerequisite_patterns} has been called in the current context reset."
                ),
            )
            for target_pattern, prerequisite_patterns in self._prerequisites.items()
        )

    def is_tool_call_permitted(
        self,
        tool_key: str,
        reset_count: int,
        cycle_index: int,
    ) -> tuple[bool, str]:
        del reset_count, cycle_index
        for target_pattern, prerequisite_patterns in self._prerequisites.items():
            if not _is_tool_allowed(tool_key, (target_pattern,)):
                continue
            if target_pattern not in self._satisfied_targets:
                return (
                    False,
                    f"waiting for prerequisite {prerequisite_patterns} before '{target_pattern}'",
                )
        return True, ""

    def record_tool_call(self, tool_key: str) -> None:
        for target_pattern, prerequisite_patterns in self._prerequisites.items():
            if any(_is_tool_allowed(tool_key, (pattern,)) for pattern in prerequisite_patterns):
                self._satisfied_targets.add(target_pattern)

    def on_post_reset(self) -> None:
        super().on_post_reset()
        self._satisfied_targets.clear()

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        lines = ["Tool sequencing prerequisites:"]
        for target_pattern, prerequisite_patterns in self._prerequisites.items():
            status = "satisfied" if target_pattern in self._satisfied_targets else "pending"
            lines.append(
                f"- {target_pattern}: {status}; requires one of {prerequisite_patterns}"
            )
        return (
            *super().get_parameter_sections(),
            AgentParameterSection(
                title=f"Behavior State: {self.layer_id}",
                content="\n".join(lines),
            ),
        )


def _is_tool_allowed(tool_key: str, patterns: tuple[str, ...]) -> bool:
    from harnessiq.tools.hooks.defaults import is_tool_allowed

    return is_tool_allowed(tool_key, patterns)
