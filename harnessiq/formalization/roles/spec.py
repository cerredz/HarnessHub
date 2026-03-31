"""
===============================================================================
File: harnessiq/formalization/roles/spec.py

What this file does:
- Defines RoleSpec, the configuration dataclass for persona injection roles.
- A role is a named identity description injected into the system prompt at a
  declared position. It is purely semantic — no tool constraints, no enforcement
  hooks, no completion logic.

Use cases:
- Declare the agent's persona by passing RoleSpec instances to RoleLayer or to
  BaseAgent(roles=[...]).

How to use it:
- Import RoleSpec from harnessiq.formalization.roles and pass one or more
  instances when constructing a RoleLayer.

Intent:
- Keep role configuration as a frozen, self-validating dataclass so persona
  declarations are explicit, inspectable, and immutable at runtime.
===============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RolePosition = Literal["top", "bottom", "after_marker"]
"""Where in the assembled system prompt a role description is injected.

"top"          — prepended before all other content.
"bottom"       — appended after all other content (including other layers).
"after_marker" — inserted immediately after the first occurrence of
                 marker_text in the assembled prompt. Falls back to "bottom"
                 with a warning when the marker is not found.
"""


@dataclass(frozen=True, slots=True)
class RoleSpec:
    """Declares one role (persona) for an agent.

    A role is a named identity description injected into the system prompt at
    a specified position. It is purely semantic — it carries no tool
    constraints, no enforcement hooks, and no completion logic.

    Note: This is distinct from the existing RoleSpec in
    harnessiq.formalization.base, which describes behavioral role-switching.
    This RoleSpec is for persona/identity injection only.
    """

    name: str
    """Short display name for this role. Used in describe() output and the
    parameter section title. Example: 'Senior Python Engineer'.
    """

    description: str
    """The persona text injected into the system prompt. Should be written in
    second person present tense, as if describing the agent's identity to
    itself.
    """

    position: RolePosition = "top"
    """Where in the assembled system prompt to inject the role description."""

    marker_text: str = ""
    """The marker string to search for when position='after_marker'.
    Case-sensitive substring match. Must be non-empty when
    position='after_marker'.
    """

    show_in_parameter_sections: bool = True
    """Whether to include the role description in the context window parameter
    sections in addition to the system prompt injection.
    """

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("RoleSpec name must not be blank.")
        if not self.description.strip():
            raise ValueError("RoleSpec description must not be blank.")
        if self.position == "after_marker" and not self.marker_text.strip():
            raise ValueError(
                "RoleSpec marker_text must be non-empty when position='after_marker'."
            )
