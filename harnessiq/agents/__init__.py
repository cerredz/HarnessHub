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
    json_parameter_section,
    render_json_parameter_content,
    estimate_text_tokens,
    json_parameter_section,
    render_json_parameter_content,
)
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
from harnessiq.shared.harness_manifests import (
    HARNESS_MANIFESTS,
    get_harness_manifest,
    list_harness_manifests,
    register_harness_manifest,
    register_harness_manifests,
)
from harnessiq.shared.linkedin import (
    ActionLogEntry,
    JobApplicationRecord,
    LinkedInAgentConfig,
    LinkedInMemoryStore,
    ScreenshotPersistor,
)
from harnessiq.utils import (
    AgentInstanceCatalog,
    AgentInstanceRecord,
    AgentInstanceStore,
    build_agent_instance_id,
    build_default_instance_name,
    fingerprint_agent_payload,
)

from .base import BaseAgent
from .provider_base import BaseProviderToolAgent
from .apollo import BaseApolloAgent
from harnessiq.shared.apollo_agent import ApolloAgentConfig, DEFAULT_APOLLO_AGENT_IDENTITY
from .email import BaseEmailAgent
from harnessiq.shared.knowt import KnowtMemoryStore
from harnessiq.shared.email import DEFAULT_EMAIL_AGENT_IDENTITY, EmailAgentConfig
from .exa import BaseExaAgent
from harnessiq.shared.exa_agent import DEFAULT_EXA_AGENT_IDENTITY, ExaAgentConfig
from .instantly import BaseInstantlyAgent
from harnessiq.shared.instantly_agent import (
    DEFAULT_INSTANTLY_AGENT_IDENTITY,
    InstantlyAgentConfig,
)
from .outreach import BaseOutreachAgent
from harnessiq.shared.outreach_agent import (
    DEFAULT_OUTREACH_AGENT_IDENTITY,
    OutreachAgentConfig,
)

from .exa_outreach import ExaOutreachAgent
from harnessiq.shared.exa_outreach import ExaOutreachMemoryStore
from .instagram import InstagramKeywordDiscoveryAgent
from harnessiq.shared.instagram import InstagramMemoryStore
from .knowt import KnowtAgent
from .leads import LeadsAgent
from .research_sweep import ResearchSweepAgent
from .linkedin import (
    LinkedInJobApplierAgent,
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
    "AgentInstanceCatalog",
    "AgentInstanceRecord",
    "AgentInstanceStore",
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
    "ApprovalPolicy",
    "BaseAgent",
    "BaseApolloAgent",
    "BaseEmailAgent",
    "BaseExaAgent",
    "BaseInstantlyAgent",
    "BaseOutreachAgent",
    "BaseProviderToolAgent",
    "ApolloAgentConfig",
    "DEFAULT_APOLLO_AGENT_IDENTITY",
    "DEFAULT_APPROVAL_POLICY",
    "ExaOutreachAgent",
    "ExaOutreachMemoryStore",
    "DEFAULT_EXA_AGENT_IDENTITY",
    "DEFAULT_EMAIL_AGENT_IDENTITY",
    "HARNESS_MANIFESTS",
    "DEFAULT_INSTANTLY_AGENT_IDENTITY",
    "DEFAULT_OUTREACH_AGENT_IDENTITY",
    "InstagramKeywordDiscoveryAgent",
    "InstagramMemoryStore",
    "KnowtAgent",
    "KnowtMemoryStore",
    "LeadsAgent",
    "ResearchSweepAgent",
    "EmailAgentConfig",
    "ExaAgentConfig",
    "InstantlyAgentConfig",
    "JobApplicationRecord",
    "LinkedInAgentConfig",
    "LinkedInJobApplierAgent",
    "LinkedInMemoryStore",
    "ScreenshotPersistor",
    "build_linkedin_browser_tool_definitions",
    "build_agent_instance_id",
    "build_default_instance_name",
    "create_linkedin_browser_stub_tools",
    "estimate_text_tokens",
    "fingerprint_agent_payload",
    "json_parameter_section",
    "get_harness_manifest",
    "HookContext",
    "HookDefinition",
    "HookHandler",
    "HookPhase",
    "HookResponse",
    "json_parameter_section",
    "list_harness_manifests",
    "register_harness_manifest",
    "register_harness_manifests",
    "normalize_linkedin_runtime_parameters",
    "render_json_parameter_content",
    "GoogleMapsProspectingAgent",
    "ProspectingAgentConfig",
    "ProspectingMemoryStore",
    "QualifiedLeadRecord",
    "RegisteredHook",
    "OutreachAgentConfig",
    "SUPPORTED_PROSPECTING_CUSTOM_PARAMETERS",
    "SUPPORTED_PROSPECTING_RUNTIME_PARAMETERS",
    "normalize_prospecting_custom_parameters",
    "normalize_prospecting_runtime_parameters",
]

try:
    from .linkedin import (
        linkedin_google_drive_binding_name,
        load_linkedin_google_drive_credentials,
        save_linkedin_google_drive_credentials,
    )
except ImportError:  # pragma: no cover - optional provider surface may be unavailable
    linkedin_google_drive_binding_name = None
    load_linkedin_google_drive_credentials = None
    save_linkedin_google_drive_credentials = None
else:
    __all__.extend(
        [
            "linkedin_google_drive_binding_name",
            "load_linkedin_google_drive_credentials",
            "save_linkedin_google_drive_credentials",
        ]
    )
