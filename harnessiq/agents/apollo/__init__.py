"""
===============================================================================
File: harnessiq/agents/apollo/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/agents/apollo` within
  the HarnessIQ runtime.
- Apollo-backed reusable agent harnesses.

Use cases:
- Import ApolloAgentRequest, ApolloAgentConfig, BaseApolloAgent,
  DEFAULT_APOLLO_AGENT_IDENTITY from one stable package entry point.
- Read this module to understand what `harnessiq/agents/apollo` intends to
  expose publicly.

How to use it:
- Import from `harnessiq/agents/apollo` when you want the supported facade
  instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/agents/apollo` explicit, discoverable,
  and easier to maintain.
===============================================================================
"""

from harnessiq.agents.apollo.agent import BaseApolloAgent
from harnessiq.shared.dtos import ApolloAgentRequest
from harnessiq.shared.apollo_agent import ApolloAgentConfig, DEFAULT_APOLLO_AGENT_IDENTITY

__all__ = [
    "ApolloAgentRequest",
    "ApolloAgentConfig",
    "BaseApolloAgent",
    "DEFAULT_APOLLO_AGENT_IDENTITY",
]
