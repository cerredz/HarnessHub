"""Compatibility wrapper for the historical Grok-only AgentModel adapter.

Factory usage (legacy CLI compatibility):
    --model-factory harnessiq.integrations.grok_model:create_grok_model

Preferred first-class usage:
    --model grok:grok-4-1-fast-reasoning

The concrete implementation now lives in `harnessiq.integrations.agent_models`.
This module stays in place so existing imports and CLI examples keep working.
"""

from __future__ import annotations

from harnessiq.integrations.agent_models import (
    DEFAULT_GROK_MODEL,
    GrokAgentModel,
    create_grok_model,
)

__all__ = ["DEFAULT_GROK_MODEL", "GrokAgentModel", "create_grok_model"]
