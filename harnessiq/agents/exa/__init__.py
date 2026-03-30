"""
===============================================================================
File: harnessiq/agents/exa/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/agents/exa` within
  the HarnessIQ runtime.
- Exa-backed reusable agent harnesses.

Use cases:
- Import BaseExaAgent, DEFAULT_EXA_AGENT_IDENTITY, ExaAgentRequest,
  ExaAgentConfig from one stable package entry point.
- Read this module to understand what `harnessiq/agents/exa` intends to expose
  publicly.

How to use it:
- Import from `harnessiq/agents/exa` when you want the supported facade instead
  of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/agents/exa` explicit, discoverable,
  and easier to maintain.
===============================================================================
"""

from harnessiq.agents.exa.agent import BaseExaAgent
from harnessiq.shared.dtos import ExaAgentRequest
from harnessiq.shared.exa_agent import DEFAULT_EXA_AGENT_IDENTITY, ExaAgentConfig

__all__ = [
    "BaseExaAgent",
    "DEFAULT_EXA_AGENT_IDENTITY",
    "ExaAgentRequest",
    "ExaAgentConfig",
]
