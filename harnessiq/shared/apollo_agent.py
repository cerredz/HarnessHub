"""Shared constants and config for Apollo-backed agent harnesses."""

from __future__ import annotations

from dataclasses import dataclass

from harnessiq.providers.apollo import ApolloCredentials
from harnessiq.shared.agents import DEFAULT_AGENT_MAX_TOKENS, DEFAULT_AGENT_RESET_THRESHOLD
from harnessiq.shared.apollo import build_apollo_operation_catalog, get_apollo_operation

DEFAULT_APOLLO_AGENT_IDENTITY = (
    "A disciplined Apollo research and prospecting agent that uses verified Apollo tool calls for "
    "search, enrichment, contact management, and sequence handoff work."
)


@dataclass(frozen=True, slots=True)
class ApolloAgentConfig:
    """Runtime configuration for reusable Apollo-backed harnesses."""

    apollo_credentials: ApolloCredentials
    allowed_apollo_operations: tuple[str, ...] | None = None
    max_tokens: int = DEFAULT_AGENT_MAX_TOKENS
    reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD

    def __post_init__(self) -> None:
        if self.allowed_apollo_operations is None:
            return
        normalized = tuple(self.allowed_apollo_operations)
        if not normalized:
            raise ValueError("allowed_apollo_operations must not be empty when provided.")
        for operation_name in normalized:
            get_apollo_operation(operation_name)
        object.__setattr__(self, "allowed_apollo_operations", normalized)


def resolve_apollo_operation_names(config: ApolloAgentConfig) -> tuple[str, ...]:
    """Return the allowed Apollo operation names for the provided config."""
    if config.allowed_apollo_operations is not None:
        return config.allowed_apollo_operations
    return tuple(operation.name for operation in build_apollo_operation_catalog())


__all__ = [
    "ApolloAgentConfig",
    "DEFAULT_APOLLO_AGENT_IDENTITY",
    "resolve_apollo_operation_names",
]
