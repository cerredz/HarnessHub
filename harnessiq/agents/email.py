"""Reusable email-capable agent harnesses built on the generic runtime."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from harnessiq.agents.base import AgentModel, AgentParameterSection, AgentRuntimeConfig, BaseAgent
from harnessiq.config import AgentCredentialBinding, ResolvedAgentCredentials, binding_field_map, resolve_credentials_input
from harnessiq.shared.tools import RegisteredTool, ToolDefinition
from harnessiq.tools.registry import ToolRegistry
from harnessiq.tools.resend import ResendClient, ResendCredentials, build_resend_operation_catalog, create_resend_tools, get_resend_operation

DEFAULT_EMAIL_AGENT_IDENTITY = (
    "A disciplined email operations agent that drafts, reviews, schedules, and sends email only "
    "through verified tool calls."
)


@dataclass(frozen=True, slots=True)
class EmailAgentConfig:
    """Runtime configuration for reusable email-capable harnesses."""

    resend_credentials: ResendCredentials | None = None
    credentials: AgentCredentialBinding | ResolvedAgentCredentials | None = None
    credentials_repo_root: Path | str = "."
    allowed_resend_operations: tuple[str, ...] | None = None
    max_tokens: int = 80_000
    reset_threshold: float = 0.9

    def __post_init__(self) -> None:
        has_direct_credentials = self.resend_credentials is not None
        has_config_credentials = self.credentials is not None
        if has_direct_credentials == has_config_credentials:
            raise ValueError("Provide exactly one of resend_credentials or credentials.")
        if self.allowed_resend_operations is None:
            normalized = None
        else:
            normalized = tuple(self.allowed_resend_operations)
            if not normalized:
                raise ValueError("allowed_resend_operations must not be empty when provided.")
            for operation_name in normalized:
                get_resend_operation(operation_name)
        object.__setattr__(self, "allowed_resend_operations", normalized)
        object.__setattr__(self, "credentials_repo_root", Path(self.credentials_repo_root))


class BaseEmailAgent(BaseAgent, ABC):
    """Abstract base harness for agents that need Resend-backed email capabilities."""

    def __init__(
        self,
        *,
        name: str,
        model: AgentModel,
        config: EmailAgentConfig,
        email_tools: Iterable[RegisteredTool] = (),
        resend_client: ResendClient | None = None,
    ) -> None:
        resolved_credentials_input = _resolve_config_credentials(config)
        resolved_resend_credentials = _resolve_resend_credentials(config, resolved_credentials_input)
        if resend_client is not None and resend_client.credentials != resolved_resend_credentials:
            raise ValueError("resend_client credentials must match EmailAgentConfig.resend_credentials.")

        self._config = config
        self._resolved_resend_credentials = resolved_resend_credentials
        self._resolved_credentials_input = resolved_credentials_input
        self._resend_client = resend_client or ResendClient(credentials=resolved_resend_credentials)

        tool_registry = ToolRegistry(
            _merge_tools(
                create_resend_tools(
                    client=self._resend_client,
                    allowed_operations=self._config.allowed_resend_operations,
                ),
                tuple(email_tools),
            )
        )
        runtime_config = AgentRuntimeConfig(
            max_tokens=self._config.max_tokens,
            reset_threshold=self._config.reset_threshold,
        )
        super().__init__(
            name=name,
            model=model,
            tool_executor=tool_registry,
            runtime_config=runtime_config,
        )

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
                content=_render_resend_credentials(self._config, self._resolved_resend_credentials, self._resolved_credentials_input),
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


def _resolve_config_credentials(config: EmailAgentConfig) -> ResolvedAgentCredentials | None:
    if config.credentials is None:
        return None
    return resolve_credentials_input(config.credentials, repo_root=config.credentials_repo_root)


def _resolve_resend_credentials(
    config: EmailAgentConfig,
    resolved_credentials: ResolvedAgentCredentials | None,
) -> ResendCredentials:
    if config.resend_credentials is not None:
        return config.resend_credentials

    if resolved_credentials is None:
        raise ValueError("EmailAgentConfig requires direct Resend credentials or a credential binding.")

    payload = resolved_credentials.as_dict()
    api_key = payload["api_key"]
    kwargs: dict[str, object] = {"api_key": api_key}
    if "base_url" in payload:
        kwargs["base_url"] = payload["base_url"]
    if "user_agent" in payload:
        kwargs["user_agent"] = payload["user_agent"]
    if "timeout_seconds" in payload:
        kwargs["timeout_seconds"] = float(payload["timeout_seconds"])
    return ResendCredentials(**kwargs)


def _render_resend_credentials(
    config: EmailAgentConfig,
    runtime_credentials: ResendCredentials,
    resolved_credentials: ResolvedAgentCredentials | None,
) -> str:
    allowed_operations = config.allowed_resend_operations
    if allowed_operations is None:
        allowed_operations = tuple(operation.name for operation in build_resend_operation_catalog())
    payload = runtime_credentials.as_redacted_dict()
    payload["allowed_operation_count"] = len(allowed_operations)
    payload["allowed_operation_sample"] = list(allowed_operations[:8])
    if isinstance(config.credentials, AgentCredentialBinding):
        payload["binding"] = binding_field_map(config.credentials)
        payload["env_path"] = str(config.credentials_repo_root / ".env")
    if resolved_credentials is not None:
        payload["resolved_fields"] = resolved_credentials.as_redacted_dict()
    return json.dumps(payload, indent=2, sort_keys=True)


def _summarize_tool(tool: ToolDefinition) -> str:
    return tool.description.splitlines()[0]


def _merge_tools(*tool_groups: Iterable[RegisteredTool]) -> tuple[RegisteredTool, ...]:
    ordered_keys: list[str] = []
    merged: dict[str, RegisteredTool] = {}
    for tool_group in tool_groups:
        for tool in tool_group:
            if tool.key not in merged:
                ordered_keys.append(tool.key)
            merged[tool.key] = tool
    return tuple(merged[key] for key in ordered_keys)


__all__ = [
    "BaseEmailAgent",
    "DEFAULT_EMAIL_AGENT_IDENTITY",
    "EmailAgentConfig",
]
