"""Portable assembled prompt bundle helpers for HarnessIQ agents."""

from __future__ import annotations

import re
from dataclasses import dataclass

from harnessiq.shared.agents import AgentParameterSection

_JSON_NUMERIC_VALUE_PATTERN = re.compile(r'(?<=: )-?\d+(?:\.\d+)?')
_STATUS_PATTERN = re.compile(
    r'(\[(?:written|not yet written|satisfied|not yet met)\]|[✓✗] (?:written|not yet written|satisfied|not yet met))'
)
_ELAPSED_PROGRESS_PATTERN = re.compile(
    r'Elapsed: [^\n]+? / [^\n]+?(?: \([\d.]+%\))?(?: [^\n]*)?'
)
_CURRENT_VALUE_PATTERN = re.compile(r'current=-?\d+(?:\.\d+)?')
_PERCENT_PATTERN = re.compile(r'\((?:-?\d+(?:\.\d+)?)%\)')


def _mask_section_values(content: str) -> str:
    """Replace live runtime values with structural placeholders."""
    masked = _JSON_NUMERIC_VALUE_PATTERN.sub("---", content)
    masked = _STATUS_PATTERN.sub("[status]", masked)
    masked = _ELAPSED_PROGRESS_PATTERN.sub("Elapsed: [elapsed] / [target]", masked)
    masked = _CURRENT_VALUE_PATTERN.sub("current=---", masked)
    masked = _PERCENT_PATTERN.sub("(--%)", masked)
    return masked


def mask_parameter_sections(
    sections: tuple[AgentParameterSection, ...] | list[AgentParameterSection],
) -> tuple[AgentParameterSection, ...]:
    """Return a copy of parameter sections with content masked for template mode."""
    return tuple(
        AgentParameterSection(
            title=section.title,
            content=_mask_section_values(section.content),
        )
        for section in sections
    )


@dataclass(frozen=True)
class MasterPromptBundle:
    """The complete assembled prompt for one agent at one point in time."""

    system_prompt: str
    parameter_sections: tuple[AgentParameterSection, ...]
    agent_name: str
    layer_count: int
    built_at_reset: int
    is_template: bool = False

    def render(self, labeled: bool = True) -> str:
        """Return the full bundle as one flat string."""
        parts = [self.system_prompt.strip()]
        for section in self.parameter_sections:
            content = section.render() if labeled else section.content.strip()
            if content:
                parts.append(content)
        return "\n\n".join(part for part in parts if part)

    def render_system_prompt_only(self) -> str:
        """Return only the fully assembled system prompt."""
        return self.system_prompt

    def render_parameter_block(self) -> str:
        """Return the parameter sections rendered as a labeled block."""
        return "\n\n".join(
            section.render()
            for section in self.parameter_sections
            if section.content.strip()
        )

    def as_additional_prompt(self) -> str:
        """Return the parameter block for injection into another harness."""
        return self.render_parameter_block()

    def summary(self) -> str:
        """Return a compact developer-facing summary."""
        lines = [
            f"Agent: {self.agent_name}",
            f"Layers: {self.layer_count}",
            f"Built at reset: {self.built_at_reset}",
            f"System prompt length: {len(self.system_prompt):,} chars",
            f"Parameter sections: {len(self.parameter_sections)}",
        ]
        for section in self.parameter_sections:
            lines.append(f"  - {section.title} ({len(section.content):,} chars)")
        return "\n".join(lines)


__all__ = [
    "MasterPromptBundle",
    "_mask_section_values",
    "mask_parameter_sections",
]
