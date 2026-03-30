"""
===============================================================================
File: harnessiq/agents/exa/agent.py

What this file does:
- Implements the concrete `BaseExaAgent` runtime for the `exa` agent package.
- The module owns the package-specific memory loading, prompt assembly, and
  tool wiring needed by that agent.
- Reusable Exa-backed agent harnesses.

Use cases:
- Instantiate the agent directly when you already have the required runtime
  parameters.
- Load the agent from persisted memory or profile helpers when resuming a
  previous run.

How to use it:
- Construct `BaseExaAgent` or use its factory helpers, then call `run()` or
  `snapshot()` through the shared base runtime.

Intent:
- Keep the `exa` workflow packaged as one reusable HarnessIQ harness instead of
  scattering its durable behavior across scripts.
===============================================================================
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Sequence

from harnessiq.agents.base import AgentModel, AgentParameterSection, AgentRuntimeConfig
from harnessiq.agents.provider_base import BaseProviderToolAgent
from harnessiq.interfaces import RequestPreparingClient
from harnessiq.providers.exa import ExaClient
from harnessiq.shared.dtos import ExaAgentRequest, ProviderToolAgentRequest
from harnessiq.shared.exceptions import ConfigurationError
from harnessiq.shared.exa_agent import DEFAULT_EXA_AGENT_IDENTITY, ExaAgentConfig, resolve_exa_operation_names
from harnessiq.shared.provider_agents import render_redacted_provider_credentials
from harnessiq.shared.tools import RegisteredTool
from harnessiq.tools.exa import create_exa_tools


class BaseExaAgent(BaseProviderToolAgent, ABC):
    """Abstract base harness for agents that need Exa-backed capabilities."""

    def __init__(
        self,
        *,
        name: str,
        model: AgentModel,
        request: ExaAgentRequest,
        tools: Sequence[RegisteredTool] | None = None,
        exa_client: RequestPreparingClient | None = None,
        runtime_config: AgentRuntimeConfig | None = None,
        memory_path: str | Path | None = None,
        repo_root: str | Path | None = None,
        instance_name: str | None = None,
    ) -> None:
        config = request.to_config()
        if exa_client is not None and exa_client.credentials != config.exa_credentials:
            raise ConfigurationError("exa_client credentials must match ExaAgentConfig.exa_credentials.")

        self._request = request
        self._config = config
        self._exa_client = exa_client or ExaClient(credentials=config.exa_credentials)
        super().__init__(
            name=name,
            model=model,
            request=ProviderToolAgentRequest(
                provider_name="Exa",
                provider_tools=create_exa_tools(
                    client=self._exa_client,
                    allowed_operations=self._config.allowed_exa_operations,
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
    def config(self) -> ExaAgentConfig:
        return self._config

    @property
    def request(self) -> ExaAgentRequest:
        return self._request

    @property
    def exa_client(self) -> RequestPreparingClient:
        return self._exa_client

    def exa_identity(self) -> str:
        """Return the default identity for Exa-backed agents."""
        return DEFAULT_EXA_AGENT_IDENTITY

    def provider_identity(self) -> str:
        return self.exa_identity()

    @abstractmethod
    def exa_objective(self) -> str:
        """Return the mission-specific goal for the concrete Exa-backed agent."""

    def provider_objective(self) -> str:
        return self.exa_objective()

    def provider_transport_guidance(self) -> str:
        return (
            "Use the configured Exa tool surface for live web search, page content retrieval, "
            "AI-grounded answers, similarity discovery, and Webset management."
        )

    def render_provider_credentials(self) -> str:
        return render_redacted_provider_credentials(
            self._config.exa_credentials.as_redacted_dict(),
            allowed_operations=resolve_exa_operation_names(self._config),
        )

    def load_exa_parameter_sections(self) -> Sequence[AgentParameterSection]:
        """Return additional durable parameter sections for the concrete Exa-backed agent."""
        return ()

    def load_provider_parameter_sections(self) -> Sequence[AgentParameterSection]:
        return self.load_exa_parameter_sections()

    def exa_behavioral_rules(self) -> Sequence[str]:
        """Return extra Exa-specific behavior rules required by a subclass."""
        return ()

    def provider_behavioral_rules(self) -> Sequence[str]:
        return (
            "Use `exa_request` for Exa search, contents, answer, similarity, and Webset operations.",
            "Base summaries and conclusions on Exa responses rather than prior assumptions.",
            *self.exa_behavioral_rules(),
        )

    def additional_exa_instructions(self) -> str | None:
        """Return optional free-form instructions appended to the system prompt."""
        return None

    def additional_provider_instructions(self) -> str | None:
        return self.additional_exa_instructions()

    def build_ledger_tags(self) -> list[str]:
        return ["exa"]

    def build_ledger_metadata(self) -> dict[str, object]:
        return {
            "allowed_exa_operations": list(resolve_exa_operation_names(self._config)),
        }


__all__ = [
    "BaseExaAgent",
    "DEFAULT_EXA_AGENT_IDENTITY",
    "ExaAgentRequest",
    "ExaAgentConfig",
]
