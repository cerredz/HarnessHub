"""Reusable Instantly-backed agent harnesses."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Sequence

from harnessiq.agents.base import AgentModel, AgentParameterSection, AgentRuntimeConfig
from harnessiq.agents.provider_base import BaseProviderToolAgent
from harnessiq.interfaces import RequestPreparingClient
from harnessiq.providers.instantly import InstantlyClient
from harnessiq.shared.dtos import InstantlyAgentRequest, ProviderToolAgentRequest
from harnessiq.shared.exceptions import ConfigurationError
from harnessiq.shared.instantly_agent import (
    DEFAULT_INSTANTLY_AGENT_IDENTITY,
    InstantlyAgentConfig,
    resolve_instantly_operation_names,
)
from harnessiq.shared.provider_agents import render_redacted_provider_credentials
from harnessiq.shared.tools import RegisteredTool
from harnessiq.tools.instantly import create_instantly_tools


class BaseInstantlyAgent(BaseProviderToolAgent, ABC):
    """Abstract base harness for agents that need Instantly-backed capabilities."""

    def __init__(
        self,
        *,
        name: str,
        model: AgentModel,
        request: InstantlyAgentRequest,
        tools: Sequence[RegisteredTool] | None = None,
        instantly_client: RequestPreparingClient | None = None,
        runtime_config: AgentRuntimeConfig | None = None,
        memory_path: str | Path | None = None,
        repo_root: str | Path | None = None,
        instance_name: str | None = None,
    ) -> None:
        config = request.to_config()
        if instantly_client is not None and instantly_client.credentials != config.instantly_credentials:
            raise ConfigurationError(
                "instantly_client credentials must match InstantlyAgentConfig.instantly_credentials."
            )

        self._request = request
        self._config = config
        self._instantly_client = instantly_client or InstantlyClient(credentials=config.instantly_credentials)
        super().__init__(
            name=name,
            model=model,
            request=ProviderToolAgentRequest(
                provider_name="Instantly",
                provider_tools=create_instantly_tools(
                    client=self._instantly_client,
                    allowed_operations=self._config.allowed_instantly_operations,
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
    def config(self) -> InstantlyAgentConfig:
        return self._config

    @property
    def request(self) -> InstantlyAgentRequest:
        return self._request

    @property
    def instantly_client(self) -> RequestPreparingClient:
        return self._instantly_client

    def instantly_identity(self) -> str:
        """Return the default identity for Instantly-backed agents."""
        return DEFAULT_INSTANTLY_AGENT_IDENTITY

    def provider_identity(self) -> str:
        return self.instantly_identity()

    @abstractmethod
    def instantly_objective(self) -> str:
        """Return the mission-specific goal for the concrete Instantly-backed agent."""

    def provider_objective(self) -> str:
        return self.instantly_objective()

    def provider_transport_guidance(self) -> str:
        return (
            "Use the configured Instantly tool surface for account, campaign, lead, label, "
            "inbox-placement, and webhook operations."
        )

    def render_provider_credentials(self) -> str:
        return render_redacted_provider_credentials(
            self._config.instantly_credentials.as_redacted_dict(),
            allowed_operations=resolve_instantly_operation_names(self._config),
        )

    def load_instantly_parameter_sections(self) -> Sequence[AgentParameterSection]:
        """Return additional durable parameter sections for the concrete Instantly-backed agent."""
        return ()

    def load_provider_parameter_sections(self) -> Sequence[AgentParameterSection]:
        return self.load_instantly_parameter_sections()

    def instantly_behavioral_rules(self) -> Sequence[str]:
        """Return extra Instantly-specific behavior rules required by a subclass."""
        return ()

    def provider_behavioral_rules(self) -> Sequence[str]:
        return (
            "Use `instantly_request` for Instantly account, campaign, lead, label, inbox-placement, and webhook operations.",
            "Verify mailbox, campaign, and lead identifiers before mutating or launching outreach state.",
            *self.instantly_behavioral_rules(),
        )

    def additional_instantly_instructions(self) -> str | None:
        """Return optional free-form instructions appended to the system prompt."""
        return None

    def additional_provider_instructions(self) -> str | None:
        return self.additional_instantly_instructions()

    def build_ledger_tags(self) -> list[str]:
        return ["instantly"]

    def build_ledger_metadata(self) -> dict[str, object]:
        return {
            "allowed_instantly_operations": list(resolve_instantly_operation_names(self._config)),
        }


__all__ = [
    "BaseInstantlyAgent",
    "DEFAULT_INSTANTLY_AGENT_IDENTITY",
    "InstantlyAgentRequest",
    "InstantlyAgentConfig",
]
