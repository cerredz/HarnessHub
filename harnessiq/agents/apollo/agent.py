"""
===============================================================================
File: harnessiq/agents/apollo/agent.py

What this file does:
- Implements the concrete `BaseApolloAgent` runtime for the `apollo` agent
  package.
- The module owns the package-specific memory loading, prompt assembly, and
  tool wiring needed by that agent.
- Reusable Apollo-backed agent harnesses.

Use cases:
- Instantiate the agent directly when you already have the required runtime
  parameters.
- Load the agent from persisted memory or profile helpers when resuming a
  previous run.

How to use it:
- Construct `BaseApolloAgent` or use its factory helpers, then call `run()` or
  `snapshot()` through the shared base runtime.

Intent:
- Keep the `apollo` workflow packaged as one reusable HarnessIQ harness instead
  of scattering its durable behavior across scripts.
===============================================================================
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Sequence

from harnessiq.agents.base import AgentModel, AgentParameterSection, AgentRuntimeConfig
from harnessiq.agents.provider_base import BaseProviderToolAgent
from harnessiq.interfaces import RequestPreparingClient
from harnessiq.providers.apollo import ApolloClient
from harnessiq.shared.dtos import ApolloAgentRequest, ProviderToolAgentRequest
from harnessiq.shared.exceptions import ConfigurationError
from harnessiq.shared.apollo_agent import (
    ApolloAgentConfig,
    DEFAULT_APOLLO_AGENT_IDENTITY,
    resolve_apollo_operation_names,
)
from harnessiq.shared.provider_agents import render_redacted_provider_credentials
from harnessiq.shared.tools import RegisteredTool
from harnessiq.tools.apollo import create_apollo_tools


class BaseApolloAgent(BaseProviderToolAgent, ABC):
    """Abstract base harness for agents that need Apollo-backed capabilities."""

    def __init__(
        self,
        *,
        name: str,
        model: AgentModel,
        request: ApolloAgentRequest,
        tools: Sequence[RegisteredTool] | None = None,
        apollo_client: RequestPreparingClient | None = None,
        runtime_config: AgentRuntimeConfig | None = None,
        memory_path: str | Path | None = None,
        repo_root: str | Path | None = None,
        instance_name: str | None = None,
    ) -> None:
        config = request.to_config()
        if apollo_client is not None and apollo_client.credentials != config.apollo_credentials:
            raise ConfigurationError(
                "apollo_client credentials must match ApolloAgentConfig.apollo_credentials."
            )

        self._request = request
        self._config = config
        self._apollo_client = apollo_client or ApolloClient(credentials=config.apollo_credentials)
        super().__init__(
            name=name,
            model=model,
            request=ProviderToolAgentRequest(
                provider_name="Apollo",
                provider_tools=create_apollo_tools(
                    client=self._apollo_client,
                    allowed_operations=self._config.allowed_apollo_operations,
                ),
                max_tokens=self._config.max_tokens,
                reset_threshold=self._config.reset_threshold,
            ),
            tools=tools,
            runtime_config=runtime_config,
            memory_path=memory_path,
            repo_root=repo_root,
            instance_name=instance_name,
        )

    @property
    def config(self) -> ApolloAgentConfig:
        return self._config

    @property
    def request(self) -> ApolloAgentRequest:
        return self._request

    @property
    def apollo_client(self) -> RequestPreparingClient:
        return self._apollo_client

    def apollo_identity(self) -> str:
        """Return the default identity for Apollo-backed agents."""
        return DEFAULT_APOLLO_AGENT_IDENTITY

    def provider_identity(self) -> str:
        return self.apollo_identity()

    @abstractmethod
    def apollo_objective(self) -> str:
        """Return the mission-specific goal for the concrete Apollo-backed agent."""

    def provider_objective(self) -> str:
        return self.apollo_objective()

    def provider_transport_guidance(self) -> str:
        return (
            "Use the configured Apollo tool surface for people search, organization search, "
            "enrichment, contact management, sequence handoff, and usage work."
        )

    def render_provider_credentials(self) -> str:
        return render_redacted_provider_credentials(
            self._config.apollo_credentials.as_redacted_dict(),
            allowed_operations=resolve_apollo_operation_names(self._config),
        )

    def load_apollo_parameter_sections(self) -> Sequence[AgentParameterSection]:
        """Return additional durable parameter sections for the concrete Apollo-backed agent."""
        return ()

    def load_provider_parameter_sections(self) -> Sequence[AgentParameterSection]:
        return self.load_apollo_parameter_sections()

    def apollo_behavioral_rules(self) -> Sequence[str]:
        """Return extra Apollo-specific behavior rules required by a subclass."""
        return ()

    def provider_behavioral_rules(self) -> Sequence[str]:
        return (
            "Use `apollo_request` for Apollo people, organization, contact, sequence, and usage operations.",
            "Confirm search and enrichment results before creating or updating Apollo contacts.",
            *self.apollo_behavioral_rules(),
        )

    def additional_apollo_instructions(self) -> str | None:
        """Return optional free-form instructions appended to the system prompt."""
        return None

    def additional_provider_instructions(self) -> str | None:
        return self.additional_apollo_instructions()

    def build_ledger_tags(self) -> list[str]:
        return ["apollo"]

    def build_ledger_metadata(self) -> dict[str, object]:
        return {
            "allowed_apollo_operations": list(resolve_apollo_operation_names(self._config)),
        }


__all__ = [
    "ApolloAgentRequest",
    "BaseApolloAgent",
    "DEFAULT_APOLLO_AGENT_IDENTITY",
    "ApolloAgentConfig",
]
