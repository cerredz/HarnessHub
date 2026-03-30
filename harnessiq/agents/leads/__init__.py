"""
===============================================================================
File: harnessiq/agents/leads/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/agents/leads` within
  the HarnessIQ runtime.
- Leads discovery agent harness.

Use cases:
- Import LEADS_CHECK_SEEN, LEADS_COMPACT_SEARCH_HISTORY, LEADS_LOG_SEARCH,
  LEADS_SAVE_LEADS, LEADS_HARNESS_MANIFEST, LeadsAgent from one stable package
  entry point.
- Read this module to understand what `harnessiq/agents/leads` intends to
  expose publicly.

How to use it:
- Import from `harnessiq/agents/leads` when you want the supported facade
  instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/agents/leads` explicit, discoverable,
  and easier to maintain.
===============================================================================
"""

from .agent import (
    LEADS_CHECK_SEEN,
    LEADS_COMPACT_SEARCH_HISTORY,
    LEADS_LOG_SEARCH,
    LEADS_SAVE_LEADS,
    LeadsAgent,
    LeadsAgentConfig,
)
from harnessiq.shared.leads import LEADS_HARNESS_MANIFEST

__all__ = [
    "LEADS_CHECK_SEEN",
    "LEADS_COMPACT_SEARCH_HISTORY",
    "LEADS_LOG_SEARCH",
    "LEADS_SAVE_LEADS",
    "LEADS_HARNESS_MANIFEST",
    "LeadsAgent",
    "LeadsAgentConfig",
]
