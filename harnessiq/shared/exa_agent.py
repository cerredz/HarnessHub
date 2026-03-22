"""Shared constants and config for Exa-backed agent harnesses."""

from __future__ import annotations

from dataclasses import dataclass

from harnessiq.providers.exa import ExaCredentials, build_exa_operation_catalog, get_exa_operation
from harnessiq.shared.agents import DEFAULT_AGENT_MAX_TOKENS, DEFAULT_AGENT_RESET_THRESHOLD

DEFAULT_EXA_AGENT_IDENTITY = (
    "A disciplined Exa research agent that uses verified Exa tool calls for live web search, "
    "content retrieval, answer generation, and Webset management."
)


@dataclass(frozen=True, slots=True)
class ExaAgentConfig:
    """Runtime configuration for reusable Exa-backed harnesses."""

    exa_credentials: ExaCredentials
    allowed_exa_operations: tuple[str, ...] | None = None
    max_tokens: int = DEFAULT_AGENT_MAX_TOKENS
    reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD

    def __post_init__(self) -> None:
        if self.allowed_exa_operations is None:
            return
        normalized = tuple(self.allowed_exa_operations)
        if not normalized:
            raise ValueError("allowed_exa_operations must not be empty when provided.")
        for operation_name in normalized:
            get_exa_operation(operation_name)
        object.__setattr__(self, "allowed_exa_operations", normalized)


def resolve_exa_operation_names(config: ExaAgentConfig) -> tuple[str, ...]:
    """Return the allowed Exa operation names for the provided config."""
    if config.allowed_exa_operations is not None:
        return config.allowed_exa_operations
    return tuple(operation.name for operation in build_exa_operation_catalog())


__all__ = [
    "DEFAULT_EXA_AGENT_IDENTITY",
    "ExaAgentConfig",
    "resolve_exa_operation_names",
]
