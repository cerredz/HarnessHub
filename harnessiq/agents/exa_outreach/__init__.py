"""
===============================================================================
File: harnessiq/agents/exa_outreach/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/agents/exa_outreach`
  within the HarnessIQ runtime.
- ExaOutreach agent harness.

Use cases:
- Import EXA_OUTREACH_HARNESS_MANIFEST, ExaOutreachAgent from one stable
  package entry point.
- Read this module to understand what `harnessiq/agents/exa_outreach` intends
  to expose publicly.

How to use it:
- Import from `harnessiq/agents/exa_outreach` when you want the supported
  facade instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/agents/exa_outreach` explicit,
  discoverable, and easier to maintain.
===============================================================================
"""

from .agent import ExaOutreachAgent
from harnessiq.shared.exa_outreach import EXA_OUTREACH_HARNESS_MANIFEST

__all__ = ["EXA_OUTREACH_HARNESS_MANIFEST", "ExaOutreachAgent"]
