"""LinkedIn job application agent harness."""

from harnessiq.agents.linkedin.agent import (
    LinkedInJobApplierAgent,
    build_linkedin_browser_tool_definitions,
    create_linkedin_browser_stub_tools,
)
from harnessiq.shared.linkedin import (
    ActionLogEntry,
    JobApplicationRecord,
    LINKEDIN_HARNESS_MANIFEST,
    LinkedInAgentConfig,
    LinkedInManagedFile,
    LinkedInMemoryStore,
    ScreenshotPersistor,
    SUPPORTED_LINKEDIN_RUNTIME_PARAMETERS,
    normalize_linkedin_runtime_parameters,
)
try:
    from harnessiq.agents.linkedin.credentials import (
        linkedin_google_drive_binding_name,
        load_linkedin_google_drive_credentials,
        save_linkedin_google_drive_credentials,
    )
except ImportError:  # pragma: no cover - optional provider surface may be unavailable
    linkedin_google_drive_binding_name = None
    load_linkedin_google_drive_credentials = None
    save_linkedin_google_drive_credentials = None

__all__ = [
    "ActionLogEntry",
    "JobApplicationRecord",
    "LINKEDIN_HARNESS_MANIFEST",
    "LinkedInAgentConfig",
    "LinkedInManagedFile",
    "LinkedInJobApplierAgent",
    "LinkedInMemoryStore",
    "ScreenshotPersistor",
    "SUPPORTED_LINKEDIN_RUNTIME_PARAMETERS",
    "build_linkedin_browser_tool_definitions",
    "create_linkedin_browser_stub_tools",
    "normalize_linkedin_runtime_parameters",
]

if linkedin_google_drive_binding_name is not None:
    __all__.extend(
        [
            "linkedin_google_drive_binding_name",
            "load_linkedin_google_drive_credentials",
            "save_linkedin_google_drive_credentials",
        ]
    )
