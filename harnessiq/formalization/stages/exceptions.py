"""
===============================================================================
File: harnessiq/formalization/stages/exceptions.py

What this file does:
- Implements part of the runtime formalization layer that turns declarative
  contracts into executable HarnessIQ behavior.
- Stage-runtime exception types.

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


class StageAdvancementError(RuntimeError):
    """Raised when a stage cannot advance to the requested destination."""


class StageCompletionError(RuntimeError):
    """Raised when stage completion payloads are invalid for the current stage."""
