"""Outreach-backed reusable agent harnesses."""

from harnessiq.agents.outreach.agent import BaseOutreachAgent
from harnessiq.shared.dtos import OutreachAgentRequest
from harnessiq.shared.outreach_agent import DEFAULT_OUTREACH_AGENT_IDENTITY, OutreachAgentConfig

__all__ = [
    "BaseOutreachAgent",
    "DEFAULT_OUTREACH_AGENT_IDENTITY",
    "OutreachAgentRequest",
    "OutreachAgentConfig",
]
