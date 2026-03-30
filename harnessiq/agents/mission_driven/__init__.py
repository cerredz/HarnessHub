"""
===============================================================================
File: harnessiq/agents/mission_driven/__init__.py

What this file does:
- Defines the package-level export surface for
  `harnessiq/agents/mission_driven` within the HarnessIQ runtime.
- Mission-driven harness package.

Use cases:
- Import MissionDrivenAgent from one stable package entry point.
- Read this module to understand what `harnessiq/agents/mission_driven` intends
  to expose publicly.

How to use it:
- Import from `harnessiq/agents/mission_driven` when you want the supported
  facade instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/agents/mission_driven` explicit,
  discoverable, and easier to maintain.
===============================================================================
"""

from .agent import MissionDrivenAgent

__all__ = ["MissionDrivenAgent"]
