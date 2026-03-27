"""Shared DTO package for explicit layer-boundary contracts."""

from .agents import (
    AgentInstancePayload,
    ApolloAgentRequest,
    EmailAgentRequest,
    ExaAgentRequest,
    InstantlyAgentRequest,
    OutreachAgentRequest,
    ProviderToolAgentRequest,
    StatelessAgentInstancePayload,
)
from .base import SerializableDTO, coerce_serializable_mapping

__all__ = [
    "AgentInstancePayload",
    "ApolloAgentRequest",
    "EmailAgentRequest",
    "ExaAgentRequest",
    "InstantlyAgentRequest",
    "OutreachAgentRequest",
    "ProviderToolAgentRequest",
    "SerializableDTO",
    "StatelessAgentInstancePayload",
    "coerce_serializable_mapping",
]
