"""Email-capable agent harnesses."""

from harnessiq.agents.email.agent import BaseEmailAgent
from harnessiq.shared.email import DEFAULT_EMAIL_AGENT_IDENTITY, EmailAgentConfig

__all__ = [
    "BaseEmailAgent",
    "DEFAULT_EMAIL_AGENT_IDENTITY",
    "EmailAgentConfig",
]
