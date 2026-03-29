"""Concrete tool cooldown behavior."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from harnessiq.shared.agents import AgentParameterSection

from .base import BaseToolBehaviorLayer, ToolConstraintSpec
from .limit import _constraint_id


class ToolCooldownBehavior(BaseToolBehaviorLayer):
    """Hide repeated tool families until an intervening tool call occurs."""

    def __init__(self, cooldowns: Mapping[str, Sequence[str]] | Sequence[str]) -> None:
        if isinstance(cooldowns, Mapping):
            self._cooldowns = {
                str(pattern): tuple(str(item) for item in required_tools if str(item).strip())
                for pattern, required_tools in cooldowns.items()
                if str(pattern).strip()
            }
        else:
            self._cooldowns = {
                str(pattern): ()
                for pattern in cooldowns
                if str(pattern).strip()
            }
        self._cooling_patterns: set[str] = set()

    def get_tool_constraints(self) -> tuple[ToolConstraintSpec, ...]:
        return tuple(
            ToolConstraintSpec(
                constraint_id=_constraint_id("TOOL_COOLDOWN", pattern),
                tool_patterns=(pattern,),
                cooldown_tools=cooldown_tools,
                description=(
                    f"Tools matching '{pattern}' cannot be called again until "
                    f"an intervening tool call{_cooldown_suffix(cooldown_tools)} occurs."
                ),
            )
            for pattern, cooldown_tools in self._cooldowns.items()
        )

    def is_tool_call_permitted(
        self,
        tool_key: str,
        reset_count: int,
        cycle_index: int,
    ) -> tuple[bool, str]:
        del reset_count, cycle_index
        for pattern in self._cooldowns:
            if _is_tool_allowed(tool_key, (pattern,)) and pattern in self._cooling_patterns:
                return False, f"cooldown active for '{pattern}'"
        return True, ""

    def record_tool_call(self, tool_key: str) -> None:
        cooled_patterns = set(self._cooling_patterns)
        for pattern, cooldown_tools in self._cooldowns.items():
            if pattern not in cooled_patterns:
                continue
            if _is_tool_allowed(tool_key, (pattern,)):
                continue
            if not cooldown_tools or any(_is_tool_allowed(tool_key, (item,)) for item in cooldown_tools):
                self._cooling_patterns.discard(pattern)

        for pattern in self._cooldowns:
            if _is_tool_allowed(tool_key, (pattern,)):
                self._cooling_patterns.add(pattern)

    def on_post_reset(self) -> None:
        super().on_post_reset()
        self._cooling_patterns.clear()

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        lines = ["Tool cooldown state:"]
        for pattern, cooldown_tools in self._cooldowns.items():
            state = "cooling" if pattern in self._cooling_patterns else "ready"
            requirement = (
                f"requires one of {cooldown_tools}"
                if cooldown_tools
                else "requires any different tool call"
            )
            lines.append(f"- {pattern}: {state}; {requirement}")
        return (
            *super().get_parameter_sections(),
            AgentParameterSection(
                title=f"Behavior State: {self.layer_id}",
                content="\n".join(lines),
            ),
        )


def _cooldown_suffix(cooldown_tools: tuple[str, ...]) -> str:
    if not cooldown_tools:
        return ""
    return f" matching {cooldown_tools}"


def _is_tool_allowed(tool_key: str, patterns: tuple[str, ...]) -> bool:
    from harnessiq.tools.hooks.defaults import is_tool_allowed

    return is_tool_allowed(tool_key, patterns)
