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
from harnessiq.shared.knowt import KnowtMemoryStore

from .exa_outreach import ExaOutreachAgent
from harnessiq.shared.exa_outreach import ExaOutreachMemoryStore
from .instagram import InstagramKeywordDiscoveryAgent
from harnessiq.shared.instagram import InstagramMemoryStore
from .knowt import KnowtAgent
from .leads import LeadsAgent
from .linkedin import (
    LinkedInJobApplierAgent,
    LinkedInMemoryStore,
    build_linkedin_browser_tool_definitions,
    create_linkedin_browser_stub_tools,
    normalize_linkedin_runtime_parameters,
)
from .prospecting import (
    GoogleMapsProspectingAgent,
    ProspectingAgentConfig,
    ProspectingMemoryStore,
    QualifiedLeadRecord,
    SUPPORTED_PROSPECTING_CUSTOM_PARAMETERS,
    SUPPORTED_PROSPECTING_RUNTIME_PARAMETERS,
    normalize_prospecting_custom_parameters,
    normalize_prospecting_runtime_parameters,
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
    "ExaOutreachAgent",
    "ExaOutreachMemoryStore",
    "DEFAULT_EMAIL_AGENT_IDENTITY",
    "InstagramKeywordDiscoveryAgent",
    "InstagramMemoryStore",
    "KnowtAgent",
    "KnowtMemoryStore",
    "LeadsAgent",
    "EmailAgentConfig",
    "InstagramKeywordDiscoveryAgent",
    "InstagramMemoryStore",
    "JobApplicationRecord",
    "LinkedInAgentConfig",
    "LinkedInJobApplierAgent",
    "LinkedInMemoryStore",
    "ScreenshotPersistor",
    "build_linkedin_browser_tool_definitions",
    "create_linkedin_browser_stub_tools",
    "estimate_text_tokens",
    "normalize_linkedin_runtime_parameters",
    "GoogleMapsProspectingAgent",
    "ProspectingAgentConfig",
    "ProspectingMemoryStore",
    "QualifiedLeadRecord",
    "SUPPORTED_PROSPECTING_CUSTOM_PARAMETERS",
    "SUPPORTED_PROSPECTING_RUNTIME_PARAMETERS",
    "normalize_prospecting_custom_parameters",
    "normalize_prospecting_runtime_parameters",
]
