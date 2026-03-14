"""Agent runtime primitives and concrete agent implementations."""

from harnessiq.shared.agents import (
    AgentModel,
    AgentModelRequest,
    AgentModelResponse,
    AgentParameterSection,
    AgentPauseSignal,
    AgentRunResult,
    AgentRunStatus,
    AgentRuntimeConfig,
    AgentToolExecutor,
    AgentTranscriptEntry,
    estimate_text_tokens,
)
from harnessiq.shared.linkedin import (
    ActionLogEntry,
    JobApplicationRecord,
    LinkedInAgentConfig,
    ScreenshotPersistor,
)

from .base import BaseAgent
from .email import BaseEmailAgent, DEFAULT_EMAIL_AGENT_IDENTITY, EmailAgentConfig
from .linkedin import (
    LinkedInJobApplierAgent,
    LinkedInMemoryStore,
    build_linkedin_browser_tool_definitions,
    create_linkedin_browser_stub_tools,
)

__all__ = [
    "ActionLogEntry",
    "AgentModel",
    "AgentModelRequest",
    "AgentModelResponse",
    "AgentParameterSection",
    "AgentPauseSignal",
    "AgentRunResult",
    "AgentRunStatus",
    "AgentRuntimeConfig",
    "AgentToolExecutor",
    "AgentTranscriptEntry",
    "BaseAgent",
    "BaseEmailAgent",
    "DEFAULT_EMAIL_AGENT_IDENTITY",
    "EmailAgentConfig",
    "JobApplicationRecord",
    "LinkedInAgentConfig",
    "LinkedInJobApplierAgent",
    "LinkedInMemoryStore",
    "ScreenshotPersistor",
    "build_linkedin_browser_tool_definitions",
    "create_linkedin_browser_stub_tools",
    "estimate_text_tokens",
]
