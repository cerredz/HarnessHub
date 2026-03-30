"""
===============================================================================
File: harnessiq/agents/outreach/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/agents/outreach`
  within the HarnessIQ runtime.
- Outreach-backed reusable agent harnesses.

Use cases:
- Import BaseOutreachAgent, DEFAULT_OUTREACH_AGENT_IDENTITY,
  OutreachAgentRequest, OutreachAgentConfig from one stable package entry
  point.
- Read this module to understand what `harnessiq/agents/outreach` intends to
  expose publicly.

How to use it:
- Import from `harnessiq/agents/outreach` when you want the supported facade
  instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/agents/outreach` explicit,
  discoverable, and easier to maintain.
===============================================================================
"""

from harnessiq.agents.outreach.agent import BaseOutreachAgent
from harnessiq.shared.dtos import OutreachAgentRequest
from harnessiq.shared.outreach_agent import DEFAULT_OUTREACH_AGENT_IDENTITY, OutreachAgentConfig

__all__ = [
    "BaseOutreachAgent",
    "DEFAULT_OUTREACH_AGENT_IDENTITY",
    "OutreachAgentRequest",
    "OutreachAgentConfig",
]
