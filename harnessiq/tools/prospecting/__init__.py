"""
===============================================================================
File: harnessiq/tools/prospecting/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/tools/prospecting`
  within the HarnessIQ runtime.
- Google Maps prospecting tool definitions and factories.

Use cases:
- Import COMPLETE_SEARCH, RECORD_LISTING_RESULT, SAVE_QUALIFIED_LEAD,
  START_SEARCH, ProspectingToolHandler, build_complete_search_tool_definition
  from one stable package entry point.
- Read this module to understand what `harnessiq/tools/prospecting` intends to
  expose publicly.

How to use it:
- Import from `harnessiq/tools/prospecting` when you want the supported facade
  instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/tools/prospecting` explicit,
  discoverable, and easier to maintain.
===============================================================================
"""

from harnessiq.tools.prospecting.operations import (
    COMPLETE_SEARCH,
    RECORD_LISTING_RESULT,
    SAVE_QUALIFIED_LEAD,
    START_SEARCH,
    ProspectingToolHandler,
    build_complete_search_tool_definition,
    build_record_listing_result_tool_definition,
    build_save_qualified_lead_tool_definition,
    build_start_search_tool_definition,
    create_complete_search_tool,
    create_record_listing_result_tool,
    create_save_qualified_lead_tool,
    create_start_search_tool,
)

__all__ = [
    "COMPLETE_SEARCH",
    "RECORD_LISTING_RESULT",
    "SAVE_QUALIFIED_LEAD",
    "START_SEARCH",
    "ProspectingToolHandler",
    "build_complete_search_tool_definition",
    "build_record_listing_result_tool_definition",
    "build_save_qualified_lead_tool_definition",
    "build_start_search_tool_definition",
    "create_complete_search_tool",
    "create_record_listing_result_tool",
    "create_save_qualified_lead_tool",
    "create_start_search_tool",
]
