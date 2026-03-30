"""
===============================================================================
File: harnessiq/agents/outreach/agent.py

What this file does:
- Implements the concrete `BaseOutreachAgent` runtime for the `outreach` agent
  package.
- The module owns the package-specific memory loading, prompt assembly, and
  tool wiring needed by that agent.
- Reusable Outreach-backed agent harnesses.

Use cases:
- Instantiate the agent directly when you already have the required runtime
  parameters.
- Load the agent from persisted memory or profile helpers when resuming a
  previous run.

How to use it:
- Construct `BaseOutreachAgent` or use its factory helpers, then call `run()`
  or `snapshot()` through the shared base runtime.

Intent:
- Keep the `outreach` workflow packaged as one reusable HarnessIQ harness
  instead of scattering its durable behavior across scripts.
===============================================================================
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Sequence

from harnessiq.agents.base import AgentModel, AgentParameterSection, AgentRuntimeConfig
from harnessiq.agents.provider_base import BaseProviderToolAgent
from harnessiq.interfaces import RequestPreparingClient
from harnessiq.providers.outreach import OutreachClient
from harnessiq.shared.dtos import OutreachAgentRequest, ProviderToolAgentRequest
from harnessiq.shared.exceptions import ConfigurationError
from harnessiq.shared.outreach_agent import (
    DEFAULT_OUTREACH_AGENT_IDENTITY,
    OutreachAgentConfig,
    resolve_outreach_operation_names,
)
from harnessiq.shared.provider_agents import render_redacted_provider_credentials
from harnessiq.shared.tools import RegisteredTool
from harnessiq.tools.outreach import create_outreach_tools


class BaseOutreachAgent(BaseProviderToolAgent, ABC):
    """Abstract base harness for agents that need Outreach-backed capabilities."""

    def __init__(
        self,
        *,
        name: str,
        model: AgentModel,
        request: OutreachAgentRequest,
        tools: Sequence[RegisteredTool] | None = None,
        outreach_client: RequestPreparingClient | None = None,
        runtime_config: AgentRuntimeConfig | None = None,
        memory_path: str | Path | None = None,
        repo_root: str | Path | None = None,
        instance_name: str | None = None,
    ) -> None:
        config = request.to_config()
        if outreach_client is not None and outreach_client.credentials != config.outreach_credentials:
            raise ConfigurationError(
                "outreach_client credentials must match OutreachAgentConfig.outreach_credentials."
            )

        self._request = request
        self._config = config
        self._outreach_client = outreach_client or OutreachClient(credentials=config.outreach_credentials)
        super().__init__(
            name=name,
            model=model,
            request=ProviderToolAgentRequest(
                provider_name="Outreach",
                provider_tools=create_outreach_tools(
                    client=self._outreach_client,
                    allowed_operations=self._config.allowed_outreach_operations,
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
    def config(self) -> OutreachAgentConfig:
        return self._config

    @property
    def request(self) -> OutreachAgentRequest:
        return self._request

    @property
    def outreach_client(self) -> RequestPreparingClient:
        return self._outreach_client

    def outreach_identity(self) -> str:
        """Return the default identity for Outreach-backed agents."""
        return DEFAULT_OUTREACH_AGENT_IDENTITY

    def provider_identity(self) -> str:
        return self.outreach_identity()

    @abstractmethod
    def outreach_objective(self) -> str:
        """Return the mission-specific goal for the concrete Outreach-backed agent."""

    def provider_objective(self) -> str:
        return self.outreach_objective()

    def provider_transport_guidance(self) -> str:
        return (
            "Use the configured Outreach tool surface for prospect, account, sequence, task, "
            "template, user, and webhook operations."
        )

    def render_provider_credentials(self) -> str:
        return render_redacted_provider_credentials(
            self._config.outreach_credentials.as_redacted_dict(),
            allowed_operations=resolve_outreach_operation_names(self._config),
        )

    def load_outreach_parameter_sections(self) -> Sequence[AgentParameterSection]:
        """Return additional durable parameter sections for the concrete Outreach-backed agent."""
        return ()

    def load_provider_parameter_sections(self) -> Sequence[AgentParameterSection]:
        return self.load_outreach_parameter_sections()

    def outreach_behavioral_rules(self) -> Sequence[str]:
        """Return extra Outreach-specific behavior rules required by a subclass."""
        return ()

    def provider_behavioral_rules(self) -> Sequence[str]:
        return (
            "Use `outreach_request` for Outreach prospect, account, sequence, task, template, user, and webhook operations.",
            "Confirm prospect, account, and sequence identifiers before mutating or deleting Outreach state.",
            *self.outreach_behavioral_rules(),
        )

    def additional_outreach_instructions(self) -> str | None:
        """Return optional free-form instructions appended to the system prompt."""
        return None

    def additional_provider_instructions(self) -> str | None:
        return self.additional_outreach_instructions()

    def build_ledger_tags(self) -> list[str]:
        return ["outreach"]

    def build_ledger_metadata(self) -> dict[str, object]:
        return {
            "allowed_outreach_operations": list(resolve_outreach_operation_names(self._config)),
        }


__all__ = [
    "BaseOutreachAgent",
    "DEFAULT_OUTREACH_AGENT_IDENTITY",
    "OutreachAgentRequest",
    "OutreachAgentConfig",
]
