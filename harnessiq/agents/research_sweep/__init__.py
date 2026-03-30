"""
===============================================================================
File: harnessiq/agents/research_sweep/__init__.py

What this file does:
- Defines the package-level export surface for
  `harnessiq/agents/research_sweep` within the HarnessIQ runtime.
- Research sweep agent package.

Use cases:
- Import ResearchSweepAgent from one stable package entry point.
- Read this module to understand what `harnessiq/agents/research_sweep` intends
  to expose publicly.

How to use it:
- Import from `harnessiq/agents/research_sweep` when you want the supported
  facade instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/agents/research_sweep` explicit,
  discoverable, and easier to maintain.
===============================================================================
"""

from .agent import ResearchSweepAgent

__all__ = ["ResearchSweepAgent"]
