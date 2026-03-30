"""
===============================================================================
File: harnessiq/agents/base/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/agents/base` within
  the HarnessIQ runtime.
- Base agent runtime abstractions.

Use cases:
- Import AgentModel, AgentModelRequest, AgentModelResponse,
  AgentParameterSection, AgentPauseSignal, AgentRunResult from one stable
  package entry point.
- Read this module to understand what `harnessiq/agents/base` intends to expose
  publicly.

How to use it:
- Import from `harnessiq/agents/base` when you want the supported facade
  instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/agents/base` explicit, discoverable,
  and easier to maintain.
===============================================================================
"""

from harnessiq.shared.hooks import (
    ApprovalPolicy,
    DEFAULT_APPROVAL_POLICY,
    HookContext,
    HookDefinition,
    HookHandler,
    HookPhase,
    HookResponse,
    RegisteredHook,
)
from harnessiq.agents.base.agent import (
    AgentModel,
    AgentModelRequest,
    AgentModelResponse,
    AgentParameterSection,
    AgentPauseSignal,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeConfig,
    AgentRuntimeSnapshot,
    AgentToolExecutor,
    AgentTranscriptEntry,
    BaseAgent,
    estimate_text_tokens,
    json_parameter_section,
    render_json_parameter_content,
)

__all__ = [
    "AgentModel",
    "AgentModelRequest",
    "AgentModelResponse",
    "AgentParameterSection",
    "AgentPauseSignal",
    "AgentRunResult",
    "AgentRunStatus",
    "AgentRuntimeConfig",
    "AgentRuntimeSnapshot",
    "AgentToolExecutor",
    "AgentTranscriptEntry",
    "ApprovalPolicy",
    "BaseAgent",
    "DEFAULT_APPROVAL_POLICY",
    "HookContext",
    "HookDefinition",
    "HookHandler",
    "HookPhase",
    "HookResponse",
    "RegisteredHook",
    "estimate_text_tokens",
    "json_parameter_section",
    "render_json_parameter_content",
]
