"""
===============================================================================
File: harnessiq/agents/subcalls.py

What this file does:
- Implements focused support logic for `harnessiq/agents`.
- Shared helpers for deterministic JSON-returning model subcalls.

Use cases:
- Import this module when sibling runtime code needs the behavior it
  centralizes.

How to use it:
- Use `parse_json_object` and the other exported symbols here through their
  package-level integration points.

Intent:
- Keep related runtime behavior centralized and easier to discover during
  maintenance.
===============================================================================
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Sequence
from typing import Any

from harnessiq.shared.agents import AgentModel, AgentModelRequest, AgentParameterSection
from harnessiq.shared.exceptions import ValidationError

JsonSubcallRunner = Callable[[str, Sequence[AgentParameterSection], str], dict[str, Any]]


def parse_json_object(raw_text: str) -> dict[str, Any]:
    """Parse one JSON object from plain text or a fenced JSON block."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValidationError("Expected JSON object response.")
    return payload


def run_json_subcall(
    model: AgentModel,
    *,
    agent_name: str,
    system_prompt: str,
    sections: Sequence[AgentParameterSection],
    label: str,
    runner: JsonSubcallRunner | None = None,
) -> dict[str, Any]:
    """Run one typed model subcall and return a parsed JSON object."""
    if runner is not None:
        payload = runner(system_prompt, sections, label)
        if not isinstance(payload, dict):
            raise ValidationError(f"{label} runner must return a JSON object mapping.")
        return payload

    response = model.generate_turn(
        AgentModelRequest(
            agent_name=f"{agent_name}.{label}",
            system_prompt=system_prompt,
            parameter_sections=tuple(sections),
            transcript=(),
            tools=(),
        )
    )
    if not response.assistant_message.strip():
        raise ValidationError(f"{label} returned empty assistant content.")
    return parse_json_object(response.assistant_message)


__all__ = ["JsonSubcallRunner", "parse_json_object", "run_json_subcall"]
