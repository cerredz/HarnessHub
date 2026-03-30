"""
===============================================================================
File: harnessiq/agents/instantly/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/agents/instantly`
  within the HarnessIQ runtime.
- Instantly-backed reusable agent harnesses.

Use cases:
- Import BaseInstantlyAgent, DEFAULT_INSTANTLY_AGENT_IDENTITY,
  InstantlyAgentRequest, InstantlyAgentConfig from one stable package entry
  point.
- Read this module to understand what `harnessiq/agents/instantly` intends to
  expose publicly.

How to use it:
- Import from `harnessiq/agents/instantly` when you want the supported facade
  instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/agents/instantly` explicit,
  discoverable, and easier to maintain.
===============================================================================
"""

from harnessiq.agents.instantly.agent import BaseInstantlyAgent
from harnessiq.shared.dtos import InstantlyAgentRequest
from harnessiq.shared.instantly_agent import DEFAULT_INSTANTLY_AGENT_IDENTITY, InstantlyAgentConfig

__all__ = [
    "BaseInstantlyAgent",
    "DEFAULT_INSTANTLY_AGENT_IDENTITY",
    "InstantlyAgentRequest",
    "InstantlyAgentConfig",
]
