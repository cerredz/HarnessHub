"""Shared DTO package for explicit layer-boundary contracts."""

from .agents import AgentInstancePayload
from .base import SerializableDTO, coerce_serializable_mapping

__all__ = [
    "AgentInstancePayload",
    "SerializableDTO",
    "coerce_serializable_mapping",
]
