"""Shared constants and config for Outreach-backed agent harnesses."""

from __future__ import annotations

from dataclasses import dataclass

from harnessiq.providers.outreach import (
    OutreachCredentials,
    build_outreach_operation_catalog,
    get_outreach_operation,
)
from harnessiq.shared.agents import DEFAULT_AGENT_MAX_TOKENS, DEFAULT_AGENT_RESET_THRESHOLD

DEFAULT_OUTREACH_AGENT_IDENTITY = (
    "A disciplined Outreach operations agent that uses verified Outreach tool calls for "
    "prospect, account, sequence, task, template, user, and webhook management."
)


@dataclass(frozen=True, slots=True)
class OutreachAgentConfig:
    """Runtime configuration for reusable Outreach-backed harnesses."""

    outreach_credentials: OutreachCredentials
    allowed_outreach_operations: tuple[str, ...] | None = None
    max_tokens: int = DEFAULT_AGENT_MAX_TOKENS
    reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD

    def __post_init__(self) -> None:
        if self.allowed_outreach_operations is None:
            return
        normalized = tuple(self.allowed_outreach_operations)
        if not normalized:
            raise ValueError("allowed_outreach_operations must not be empty when provided.")
        for operation_name in normalized:
            get_outreach_operation(operation_name)
        object.__setattr__(self, "allowed_outreach_operations", normalized)


def resolve_outreach_operation_names(config: OutreachAgentConfig) -> tuple[str, ...]:
    """Return the allowed Outreach operation names for the provided config."""
    if config.allowed_outreach_operations is not None:
        return config.allowed_outreach_operations
    return tuple(operation.name for operation in build_outreach_operation_catalog())


__all__ = [
    "DEFAULT_OUTREACH_AGENT_IDENTITY",
    "OutreachAgentConfig",
    "resolve_outreach_operation_names",
]
