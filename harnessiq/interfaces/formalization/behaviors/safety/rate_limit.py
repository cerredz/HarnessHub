"""Concrete rate-limit behavior."""

from __future__ import annotations

from harnessiq.shared.agents import AgentParameterSection
from harnessiq.shared.tools import ToolResult

from .base import BaseSafetyBehaviorLayer, GuardrailSpec, _is_tool_allowed


class RateLimitBehavior(BaseSafetyBehaviorLayer):
    """Limit how often protected tools may be called."""

    def __init__(
        self,
        *,
        limits: dict[str, int],
        window: str = "reset",
        cooldown_cycles: int = 0,
    ) -> None:
        if window not in {"reset", "run"}:
            raise ValueError("window must be either 'reset' or 'run'.")
        if cooldown_cycles < 0:
            raise ValueError("cooldown_cycles must not be negative.")
        if any(count <= 0 for count in limits.values()):
            raise ValueError("All rate-limit counts must be greater than zero.")
        self._limits = {pattern: count for pattern, count in limits.items()}
        self._window = window
        self._cooldown_cycles = cooldown_cycles
        self._calls_this_run: dict[str, int] = {}
        self._calls_this_reset: dict[str, int] = {}
        self._last_called_cycle: dict[str, int] = {}
        self._cycle_index = 0

    def get_guardrails(self) -> tuple[GuardrailSpec, ...]:
        return tuple(
            GuardrailSpec(
                guardrail_id=f"RATE_LIMIT_{pattern.replace('*', 'X').replace('.', '_').upper()}",
                description=(
                    f"Tools matching {pattern} may be called at most {limit} time(s) per {self._window}"
                    + (
                        f" and remain hidden for {self._cooldown_cycles} cycle(s) after each call."
                        if self._cooldown_cycles > 0
                        else "."
                    )
                ),
                protected_patterns=(pattern,),
                rate_limit_n=limit,
            )
            for pattern, limit in self._limits.items()
        )

    def is_guardrail_satisfied(self, guardrail: GuardrailSpec, tool_key: str) -> bool:
        limit = guardrail.rate_limit_n
        if limit is None:
            return True
        count = self._family_count(tool_key, guardrail.protected_patterns)
        if count >= limit:
            return False
        if self._cooldown_cycles <= 0:
            return True
        last_cycle = self._family_last_cycle(tool_key, guardrail.protected_patterns)
        if last_cycle is None:
            return True
        return (self._cycle_index - last_cycle) >= self._cooldown_cycles

    def on_tool_result(self, result: ToolResult) -> ToolResult:
        self._cycle_index += 1
        for pattern in self._limits:
            if not _is_tool_allowed(result.tool_key, (pattern,)):
                continue
            self._calls_this_run[result.tool_key] = self._calls_this_run.get(result.tool_key, 0) + 1
            self._calls_this_reset[result.tool_key] = self._calls_this_reset.get(result.tool_key, 0) + 1
            self._last_called_cycle[result.tool_key] = self._cycle_index
        return result

    def on_agent_prepare(self, *, agent_name: str, memory_path: str) -> None:
        del agent_name, memory_path
        self._calls_this_run.clear()
        self._calls_this_reset.clear()
        self._last_called_cycle.clear()
        self._cycle_index = 0

    def on_post_reset(self) -> None:
        if self._window == "reset":
            self._calls_this_reset.clear()

    def _family_count(self, tool_key: str, patterns: tuple[str, ...]) -> int:
        counts = self._calls_this_reset if self._window == "reset" else self._calls_this_run
        return sum(
            count
            for candidate_key, count in counts.items()
            if any(_is_tool_allowed(candidate_key, (pattern,)) for pattern in patterns)
            and any(_is_tool_allowed(tool_key, (pattern,)) for pattern in patterns)
        )

    def _family_last_cycle(self, tool_key: str, patterns: tuple[str, ...]) -> int | None:
        matching_cycles = [
            cycle
            for candidate_key, cycle in self._last_called_cycle.items()
            if any(_is_tool_allowed(candidate_key, (pattern,)) for pattern in patterns)
            and any(_is_tool_allowed(tool_key, (pattern,)) for pattern in patterns)
        ]
        if not matching_cycles:
            return None
        return max(matching_cycles)

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        lines = [f"Window: {self._window}", f"Cooldown cycles: {self._cooldown_cycles}"]
        for pattern, limit in self._limits.items():
            counts = self._calls_this_reset if self._window == "reset" else self._calls_this_run
            used = sum(
                count
                for candidate_key, count in counts.items()
                if _is_tool_allowed(candidate_key, (pattern,))
            )
            lines.append(f"{pattern}: {used}/{limit} used")
        return (
            *super().get_parameter_sections(),
            AgentParameterSection(title=f"Behavior State: {self.layer_id}", content="\n".join(lines)),
        )


__all__ = ["RateLimitBehavior"]
