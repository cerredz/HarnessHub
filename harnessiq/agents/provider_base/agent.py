"""Reusable provider-backed agent harness scaffolding."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable, Sequence

from harnessiq.agents.base import AgentModel, AgentParameterSection, AgentRuntimeConfig, BaseAgent
from harnessiq.shared.agents import merge_agent_runtime_config
from harnessiq.shared.provider_agents import (
    DEFAULT_PROVIDER_AGENT_IDENTITY,
    build_provider_tool_system_prompt,
    merge_registered_tools,
)
from harnessiq.shared.tools import RegisteredTool, ToolDefinition
from harnessiq.tools.registry import ToolRegistry


class BaseProviderToolAgent(BaseAgent, ABC):
    """Abstract base harness for agents backed by a default provider tool surface."""

    def __init__(
        self,
        *,
        name: str,
        model: AgentModel,
        provider_name: str,
        provider_tools: Iterable[RegisteredTool],
        tools: Sequence[RegisteredTool] | None = None,
        max_tokens: int,
        reset_threshold: float,
        runtime_config: AgentRuntimeConfig | None = None,
    ) -> None:
        normalized_provider_name = provider_name.strip()
        if not normalized_provider_name:
            raise ValueError("provider_name must not be blank.")

        merged_provider_tools = merge_registered_tools(tuple(provider_tools))
        if not merged_provider_tools:
            raise ValueError("provider_tools must contain at least one registered tool.")

        self._provider_name = normalized_provider_name
        self._provider_tools = merged_provider_tools
        tool_registry = ToolRegistry(
            merge_registered_tools(
                self._provider_tools,
                tuple(tools or ()),
            )
        )
        super().__init__(
            name=name,
            model=model,
            tool_executor=tool_registry,
            runtime_config=merge_agent_runtime_config(
                runtime_config,
                max_tokens=max_tokens,
                reset_threshold=reset_threshold,
            ),
        )

    def build_instance_payload(self) -> dict[str, Any]:
        return {}

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def provider_tools(self) -> tuple[RegisteredTool, ...]:
        return self._provider_tools

    @property
    def provider_tool_definitions(self) -> tuple[ToolDefinition, ...]:
        return tuple(tool.definition for tool in self._provider_tools)

    @property
    def primary_provider_tool(self) -> ToolDefinition:
        return self._provider_tools[0].definition

    def build_system_prompt(self) -> str:
        behavioral_rules = (
            *self._default_behavioral_rules(),
            *self.provider_behavioral_rules(),
        )
        return build_provider_tool_system_prompt(
            identity=self.provider_identity(),
            objective=self.provider_objective(),
            transport_guidance=self.provider_transport_guidance(),
            tools=self.available_tools(),
            behavioral_rules=behavioral_rules,
            additional_instructions=self.additional_provider_instructions(),
        )

    def load_parameter_sections(self) -> Sequence[AgentParameterSection]:
        sections: list[AgentParameterSection] = []
        credential_content = self.render_provider_credentials().strip()
        if credential_content:
            sections.append(
                AgentParameterSection(
                    title=self.provider_credentials_section_title(),
                    content=credential_content,
                )
            )
        sections.extend(self.load_provider_parameter_sections())
        return tuple(sections)

    def provider_identity(self) -> str:
        """Return the default identity for provider-backed agents."""
        return DEFAULT_PROVIDER_AGENT_IDENTITY

    @abstractmethod
    def provider_objective(self) -> str:
        """Return the mission-specific goal for the concrete provider-backed agent."""

    def provider_transport_guidance(self) -> str:
        """Return transport guidance for the provider tool surface."""
        return (
            f"Use the configured {self.provider_name} tool surface for all provider-backed work. "
            f"Prefer `{self.primary_provider_tool.name}` for {self.provider_name} reads and writes."
        )

    def provider_credentials_section_title(self) -> str:
        """Return the title used for the provider credential parameter section."""
        return f"{self.provider_name} Credentials"

    @abstractmethod
    def render_provider_credentials(self) -> str:
        """Return the rendered provider credential parameter content."""

    def load_provider_parameter_sections(self) -> Sequence[AgentParameterSection]:
        """Return additional durable parameter sections for the concrete provider-backed agent."""
        return ()

    def provider_behavioral_rules(self) -> Sequence[str]:
        """Return extra provider-specific behavior rules required by a subclass."""
        return ()

    def additional_provider_instructions(self) -> str | None:
        """Return optional free-form instructions appended to the system prompt."""
        return None

    def _default_behavioral_rules(self) -> tuple[str, ...]:
        return (
            f"Use `{self.primary_provider_tool.name}` for every {self.provider_name} API interaction.",
            "Never claim a provider action succeeded until a tool result confirms it.",
            "Verify identifiers, filters, and payloads before mutating remote provider state.",
            "Do not expose raw API credentials or secrets in assistant messages.",
        )


__all__ = ["BaseProviderToolAgent"]
