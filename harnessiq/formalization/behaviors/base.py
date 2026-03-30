"""
===============================================================================
File: harnessiq/formalization/behaviors/base.py

What this file does:
- Implements part of the runtime formalization layer that turns declarative
  contracts into executable HarnessIQ behavior.
- Legacy-compatible exports for behavior-layer base types.

Use cases:
- Use this module when wiring staged execution, artifacts, or reusable
  formalization runtime helpers into an agent.

How to use it:
- Import the runtime classes or helpers from this module through the
  formalization package and compose them into the agent runtime.

Intent:
- Make formalization rules operational in Python so important workflow
  constraints are enforced deterministically.
===============================================================================
"""

from harnessiq.interfaces.formalization.behaviors import (
    BaseBehaviorLayer,
    BehaviorConstraint,
    BehaviorEnforcementMode,
    BehaviorViolationAction,
)

__all__ = [
    "BaseBehaviorLayer",
    "BehaviorConstraint",
    "BehaviorEnforcementMode",
    "BehaviorViolationAction",
]
