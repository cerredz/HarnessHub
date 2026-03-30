"""
===============================================================================
File: harnessiq/agents/knowt/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/agents/knowt` within
  the HarnessIQ runtime.
- Knowt TikTok content creation agent.

Use cases:
- Import KNOWT_HARNESS_MANIFEST, KnowtAgent from one stable package entry
  point.
- Read this module to understand what `harnessiq/agents/knowt` intends to
  expose publicly.

How to use it:
- Import from `harnessiq/agents/knowt` when you want the supported facade
  instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/agents/knowt` explicit, discoverable,
  and easier to maintain.
===============================================================================
"""

from .agent import KnowtAgent
from harnessiq.shared.knowt import KNOWT_HARNESS_MANIFEST

__all__ = ["KNOWT_HARNESS_MANIFEST", "KnowtAgent"]
