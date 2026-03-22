"""Shared constants and config for email-capable agent harnesses."""

from __future__ import annotations

from dataclasses import dataclass

from harnessiq.shared.agents import DEFAULT_AGENT_MAX_TOKENS, DEFAULT_AGENT_RESET_THRESHOLD
from harnessiq.tools.resend import ResendCredentials, get_resend_operation

DEFAULT_EMAIL_AGENT_IDENTITY = (
    "A disciplined email operations agent that drafts, reviews, schedules, and sends email only "
    "through verified tool calls."
)


@dataclass(frozen=True, slots=True)
class EmailAgentConfig:
    """Runtime configuration for reusable email-capable harnesses."""

    resend_credentials: ResendCredentials
    allowed_resend_operations: tuple[str, ...] | None = None
    max_tokens: int = DEFAULT_AGENT_MAX_TOKENS
    reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD

    def __post_init__(self) -> None:
        if self.allowed_resend_operations is None:
            return
        normalized = tuple(self.allowed_resend_operations)
        if not normalized:
            raise ValueError("allowed_resend_operations must not be empty when provided.")
        for operation_name in normalized:
            get_resend_operation(operation_name)
        object.__setattr__(self, "allowed_resend_operations", normalized)


__all__ = [
    "DEFAULT_EMAIL_AGENT_IDENTITY",
    "EmailAgentConfig",
]
