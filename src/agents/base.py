"""Abstract runtime-capable agent base."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from src.providers.anthropic.helpers import build_request as build_anthropic_request
from src.providers.base import ProviderMessage, ProviderName, SUPPORTED_PROVIDERS
from src.providers.gemini.helpers import build_request as build_gemini_request
from src.providers.grok.helpers import build_request as build_grok_request
from src.providers.openai.helpers import build_request as build_openai_request
from src.tools.registry import ToolRegistry, create_builtin_registry
from src.tools.schemas import ToolArguments, ToolDefinition, ToolResult

RequestBuilder = Callable[[str, str, list[ProviderMessage], list[ToolDefinition]], dict[str, object]]

_REQUEST_BUILDERS: dict[ProviderName, RequestBuilder] = {
    "anthropic": build_anthropic_request,
    "openai": build_openai_request,
    "grok": build_grok_request,
    "gemini": build_gemini_request,
}


class UnsupportedProviderError(ValueError):
    """Raised when an agent references an unknown provider."""


class AgentToolAccessError(PermissionError):
    """Raised when an agent attempts to use a tool outside its configured set."""


class AgentConfigurationError(ValueError):
    """Raised when an agent is initialized with invalid runtime configuration."""


@dataclass(slots=True)
class BaseAgent(ABC):
    """Shared runtime behavior for future concrete harness agents."""

    name: str
    model_name: str
    system_prompt: str
    tools: Sequence[str]
    provider: ProviderName
    registry: ToolRegistry = field(default_factory=create_builtin_registry, repr=False)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise AgentConfigurationError("Agent name must not be blank.")
        if not self.model_name.strip():
            raise AgentConfigurationError("Agent model_name must not be blank.")
        if self.provider not in SUPPORTED_PROVIDERS:
            message = f"Unsupported provider '{self.provider}'."
            raise UnsupportedProviderError(message)
        self.tools = tuple(self.tools)
        self.registry.select(self.tools)

    @property
    def tool_definitions(self) -> list[ToolDefinition]:
        """Resolve configured tools into canonical metadata objects."""
        return self.registry.definitions(self.tools)

    def build_request(self, messages: list[ProviderMessage]) -> dict[str, object]:
        """Build a provider-ready request body for the configured model."""
        builder = _REQUEST_BUILDERS[self.provider]
        return builder(self.model_name, self.system_prompt, messages, self.tool_definitions)

    def execute_tool(self, tool_key: str, arguments: ToolArguments) -> ToolResult:
        """Execute one of the agent's configured tools locally."""
        if tool_key not in self.tools:
            message = f"Agent '{self.name}' is not configured to use tool '{tool_key}'."
            raise AgentToolAccessError(message)
        return self.registry.execute(tool_key, arguments)

    @abstractmethod
    def invoke(self, messages: list[ProviderMessage]) -> Any:
        """Run the provider-specific transport for this agent."""
