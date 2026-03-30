"""
===============================================================================
File: harnessiq/agents/prospecting/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/agents/prospecting`
  within the HarnessIQ runtime.
- Google Maps prospecting agent harness.

Use cases:
- Import GoogleMapsProspectingAgent, ProspectingAgentConfig,
  ProspectingMemoryStore, PROSPECTING_HARNESS_MANIFEST, QualifiedLeadRecord,
  SUPPORTED_PROSPECTING_CUSTOM_PARAMETERS from one stable package entry point.
- Read this module to understand what `harnessiq/agents/prospecting` intends to
  expose publicly.

How to use it:
- Import from `harnessiq/agents/prospecting` when you want the supported facade
  instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/agents/prospecting` explicit,
  discoverable, and easier to maintain.
===============================================================================
"""

from .agent import GoogleMapsProspectingAgent
from harnessiq.shared.prospecting import (
    ProspectingAgentConfig,
    ProspectingMemoryStore,
    PROSPECTING_HARNESS_MANIFEST,
    QualifiedLeadRecord,
    SUPPORTED_PROSPECTING_CUSTOM_PARAMETERS,
    SUPPORTED_PROSPECTING_RUNTIME_PARAMETERS,
    normalize_prospecting_custom_parameters,
    normalize_prospecting_runtime_parameters,
)

__all__ = [
    "GoogleMapsProspectingAgent",
    "ProspectingAgentConfig",
    "ProspectingMemoryStore",
    "PROSPECTING_HARNESS_MANIFEST",
    "QualifiedLeadRecord",
    "SUPPORTED_PROSPECTING_CUSTOM_PARAMETERS",
    "SUPPORTED_PROSPECTING_RUNTIME_PARAMETERS",
    "normalize_prospecting_custom_parameters",
    "normalize_prospecting_runtime_parameters",
]
