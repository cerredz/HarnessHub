"""Reusable email-capable agent harnesses built on the generic runtime."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, Sequence

from harnessiq.agents.base import AgentModel, AgentParameterSection, AgentRuntimeConfig, BaseAgent
from harnessiq.agents.email.helpers import (
    render_resend_credentials as _render_resend_credentials,
    summarize_tool as _summarize_tool,
)
from harnessiq.shared.agents import merge_agent_runtime_config
from harnessiq.shared.exceptions import ConfigurationError
from harnessiq.shared.email import DEFAULT_EMAIL_AGENT_IDENTITY, EmailAgentConfig
from harnessiq.shared.tools import RegisteredTool, ToolDefinition
from harnessiq.tools.registry import create_tool_registry
from harnessiq.tools.resend import ResendClient, ResendCredentials, create_resend_tools


class BaseEmailAgent(BaseAgent, ABC):
    """Abstract base harness for agents that need Resend-backed email capabilities."""

    def __init__(
        self,
        *,
        name: str,
        model: AgentModel,
        config: EmailAgentConfig,
        email_tools: Iterable[RegisteredTool] = (),
        tools: Sequence[RegisteredTool] | None = None,
        resend_client: ResendClient | None = None,
        runtime_config: AgentRuntimeConfig | None = None,
    ) -> None:
        if resend_client is not None and resend_client.credentials != config.resend_credentials:
            raise ConfigurationError(
                "resend_client credentials must match EmailAgentConfig.resend_credentials."
            )

        self._config = config
        self._resend_client = resend_client or ResendClient(credentials=config.resend_credentials)

        tool_registry = create_tool_registry(
            create_resend_tools(
                client=self._resend_client,
                allowed_operations=self._config.allowed_resend_operations,
            ),
            tuple(email_tools),
            tuple(tools or ()),
        )
        super().__init__(
            name=name,
            model=model,
            tool_executor=tool_registry,
            runtime_config=merge_agent_runtime_config(
                runtime_config,
                max_tokens=self._config.max_tokens,
                reset_threshold=self._config.reset_threshold,
            ),
        )

    def build_instance_payload(self) -> dict:
        return {}

    @property
    def config(self) -> EmailAgentConfig:
        return self._config

    @property
    def resend_client(self) -> ResendClient:
        return self._resend_client

    def build_system_prompt(self) -> str:
        tool_lines = [f"- {tool.name}: {_summarize_tool(tool)}" for tool in self.available_tools()]
        behavioral_rules = [
            "- Use `resend_request` for every outbound email, list, contact, template, broadcast, domain, or webhook action.",
            "- Never claim an email was sent until a tool result returns a Resend identifier or success payload.",
            "- Prefer `idempotency_key` when retrying a send that should not duplicate delivery.",
            "- Verify domains, recipients, contacts, segments, and templates before sending at scale.",
            "- Do not expose raw API credentials or secrets in assistant messages.",
            *self.email_behavioral_rules(),
        ]
        sections = [
            "[IDENTITY]",
            self.email_identity(),
            "[GOAL]",
            self.email_objective(),
            "[TRANSPORT]",
            "Use the configured Resend tool surface for all delivery and email-operations work.",
            "[TOOLS]",
            "\n".join(tool_lines),
            "[BEHAVIORAL RULES]",
            "\n".join(behavioral_rules),
        ]
        additional = self.additional_email_instructions()
        if additional:
            sections.extend(["[ADDITIONAL INSTRUCTIONS]", additional])
        return "\n\n".join(section for section in sections if section)

    def load_parameter_sections(self) -> Sequence[AgentParameterSection]:
        return (
            AgentParameterSection(
                title="Resend Credentials",
                content=_render_resend_credentials(self._config),
            ),
            *self.load_email_parameter_sections(),
        )

    def email_identity(self) -> str:
        """Return the default identity for email-capable agents."""
        return DEFAULT_EMAIL_AGENT_IDENTITY

    @abstractmethod
    def email_objective(self) -> str:
        """Return the mission-specific goal for the concrete email agent."""

    @abstractmethod
    def load_email_parameter_sections(self) -> Sequence[AgentParameterSection]:
        """Return additional durable parameter sections for the concrete email agent."""

    def email_behavioral_rules(self) -> Sequence[str]:
        """Return any extra behavior rules required by a subclass."""
        return ()

    def additional_email_instructions(self) -> str | None:
        """Return optional free-form instructions appended to the system prompt."""
        return None

    def build_ledger_tags(self) -> list[str]:
        return ["email"]

    def build_ledger_metadata(self) -> dict[str, object]:
        return {
            "allowed_resend_operations": list(self._config.allowed_resend_operations or ()),
        }
__all__ = [
    "BaseEmailAgent",
    "DEFAULT_EMAIL_AGENT_IDENTITY",
    "EmailAgentConfig",
]
