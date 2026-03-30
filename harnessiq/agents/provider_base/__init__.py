"""
===============================================================================
File: harnessiq/agents/provider_base/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/agents/provider_base`
  within the HarnessIQ runtime.
- Provider-backed reusable agent harnesses.

Use cases:
- Import BaseProviderToolAgent from one stable package entry point.
- Read this module to understand what `harnessiq/agents/provider_base` intends
  to expose publicly.

How to use it:
- Import from `harnessiq/agents/provider_base` when you want the supported
  facade instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/agents/provider_base` explicit,
  discoverable, and easier to maintain.
===============================================================================
"""

from harnessiq.agents.provider_base.agent import BaseProviderToolAgent

__all__ = ["BaseProviderToolAgent"]
