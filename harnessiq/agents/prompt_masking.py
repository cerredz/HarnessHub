"""
===============================================================================
File: harnessiq/agents/prompt_masking.py

What this file does:
- Provides the canonical masking utilities for prompt parameter sections used
  in template-mode prompt rendering.
- Extracted as a standalone module so that both `prompt_bundle.py` and
  `harnessiq.agents.base.agent_helpers` can import from a single neutral
  location without creating circular or parent-child import dependencies.

Use cases:
- Import `mask_parameter_sections` when you need to replace live runtime
  values in assembled parameter sections with structural placeholders.

Intent:
- Serve as the third module that eliminates the mutual import between
  `harnessiq.agents.prompt_bundle` and `harnessiq.agents.base.agent_helpers`.
===============================================================================
"""

from __future__ import annotations

import re

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
    """Replace live runtime values in section content with structural placeholders."""
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


__all__ = [
    "_mask_section_values",
    "mask_parameter_sections",
]
