"""Shared DTO package for explicit layer-boundary contracts."""

from .agents import (
    AgentInstancePayload,
    ApolloAgentRequest,
    EmailAgentRequest,
    ExaOutreachAgentInstancePayload,
    ExaAgentRequest,
    InstagramAgentInstancePayload,
    InstantlyAgentRequest,
    KnowtAgentInstancePayload,
    LeadsAgentInstancePayload,
    LinkedInAgentInstancePayload,
    OutreachAgentRequest,
    ProspectingAgentInstancePayload,
    ProviderToolAgentRequest,
    ResearchSweepAgentInstancePayload,
    StatelessAgentInstancePayload,
)
from .base import SerializableDTO, coerce_serializable_mapping

__all__ = [
    "AgentInstancePayload",
    "ApolloAgentRequest",
    "EmailAgentRequest",
    "ExaOutreachAgentInstancePayload",
    "ExaAgentRequest",
    "InstagramAgentInstancePayload",
    "InstantlyAgentRequest",
    "KnowtAgentInstancePayload",
    "LeadsAgentInstancePayload",
    "LinkedInAgentInstancePayload",
    "OutreachAgentRequest",
    "ProspectingAgentInstancePayload",
    "ProviderToolAgentRequest",
    "ResearchSweepAgentInstancePayload",
    "SerializableDTO",
    "StatelessAgentInstancePayload",
    "coerce_serializable_mapping",
]
