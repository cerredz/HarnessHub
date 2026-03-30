"""
===============================================================================
File: harnessiq/agents/instagram/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/agents/instagram`
  within the HarnessIQ runtime.
- Instagram keyword discovery agent harness.

Use cases:
- Import INSTAGRAM_HARNESS_MANIFEST, InstagramKeywordDiscoveryAgent from one
  stable package entry point.
- Read this module to understand what `harnessiq/agents/instagram` intends to
  expose publicly.

How to use it:
- Import from `harnessiq/agents/instagram` when you want the supported facade
  instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/agents/instagram` explicit,
  discoverable, and easier to maintain.
===============================================================================
"""

from .agent import InstagramKeywordDiscoveryAgent
from harnessiq.shared.instagram import INSTAGRAM_HARNESS_MANIFEST

__all__ = ["INSTAGRAM_HARNESS_MANIFEST", "InstagramKeywordDiscoveryAgent"]
