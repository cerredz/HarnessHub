"""
===============================================================================
File: harnessiq/tools/search/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/tools/search` within
  the HarnessIQ runtime.
- Shared search tool factories.

Use cases:
- Import build_search_or_summarize_tool_definition,
  create_search_or_summarize_tool from one stable package entry point.
- Read this module to understand what `harnessiq/tools/search` intends to
  expose publicly.

How to use it:
- Import from `harnessiq/tools/search` when you want the supported facade
  instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/tools/search` explicit, discoverable,
  and easier to maintain.
===============================================================================
"""

from .search_or_summarize import (
    build_search_or_summarize_tool_definition,
    create_search_or_summarize_tool,
)

__all__ = [
    "build_search_or_summarize_tool_definition",
    "create_search_or_summarize_tool",
]
