"""
===============================================================================
File: harnessiq/formalization/artifacts/exceptions.py

What this file does:
- Implements part of the runtime formalization layer that turns declarative
  contracts into executable HarnessIQ behavior.
- Artifact-formalization runtime exception types.

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


class ArtifactNotFoundError(FileNotFoundError):
    """Raised when a required input artifact is not present on disk."""


class OutputArtifactMissingError(RuntimeError):
    """Raised when required output artifacts are still missing."""


__all__ = ["ArtifactNotFoundError", "OutputArtifactMissingError"]
