"""Shared constants and config for Instantly-backed agent harnesses."""

from __future__ import annotations

from dataclasses import dataclass

from harnessiq.providers.instantly import (
    InstantlyCredentials,
    build_instantly_operation_catalog,
    get_instantly_operation,
)
from harnessiq.shared.agents import DEFAULT_AGENT_MAX_TOKENS, DEFAULT_AGENT_RESET_THRESHOLD

DEFAULT_INSTANTLY_AGENT_IDENTITY = (
    "A disciplined Instantly operations agent that uses verified Instantly tool calls for mailbox, "
    "campaign, lead, label, inbox-placement, and webhook management."
)


@dataclass(frozen=True, slots=True)
class InstantlyAgentConfig:
    """Runtime configuration for reusable Instantly-backed harnesses."""

    instantly_credentials: InstantlyCredentials
    allowed_instantly_operations: tuple[str, ...] | None = None
    max_tokens: int = DEFAULT_AGENT_MAX_TOKENS
    reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD

    def __post_init__(self) -> None:
        if self.allowed_instantly_operations is None:
            return
        normalized = tuple(self.allowed_instantly_operations)
        if not normalized:
            raise ValueError("allowed_instantly_operations must not be empty when provided.")
        for operation_name in normalized:
            get_instantly_operation(operation_name)
        object.__setattr__(self, "allowed_instantly_operations", normalized)


def resolve_instantly_operation_names(config: InstantlyAgentConfig) -> tuple[str, ...]:
    """Return the allowed Instantly operation names for the provided config."""
    if config.allowed_instantly_operations is not None:
        return config.allowed_instantly_operations
    return tuple(operation.name for operation in build_instantly_operation_catalog())


__all__ = [
    "DEFAULT_INSTANTLY_AGENT_IDENTITY",
    "InstantlyAgentConfig",
    "resolve_instantly_operation_names",
]
