"""
===============================================================================
File: harnessiq/agents/email/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/agents/email` within
  the HarnessIQ runtime.
- Email-capable agent harnesses.

Use cases:
- Import BaseEmailAgent, DEFAULT_EMAIL_AGENT_IDENTITY, EmailCampaignAgent,
  EmailAgentRequest, EmailAgentConfig from one stable package entry point.
- Read this module to understand what `harnessiq/agents/email` intends to
  expose publicly.

How to use it:
- Import from `harnessiq/agents/email` when you want the supported facade
  instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/agents/email` explicit, discoverable,
  and easier to maintain.
===============================================================================
"""

from harnessiq.agents.email.agent import BaseEmailAgent
from harnessiq.agents.email.campaign import EmailCampaignAgent
from harnessiq.shared.dtos import EmailAgentRequest
from harnessiq.shared.email import DEFAULT_EMAIL_AGENT_IDENTITY, EmailAgentConfig

__all__ = [
    "BaseEmailAgent",
    "DEFAULT_EMAIL_AGENT_IDENTITY",
    "EmailCampaignAgent",
    "EmailAgentRequest",
    "EmailAgentConfig",
]
