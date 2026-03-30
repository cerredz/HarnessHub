"""
===============================================================================
File: harnessiq/tools/leadiq/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/tools/leadiq` within
  the HarnessIQ runtime.
- LeadIQ MCP-style tool factory.

Use cases:
- Import build_leadiq_request_tool_definition, create_leadiq_tools from one
  stable package entry point.
- Read this module to understand what `harnessiq/tools/leadiq` intends to
  expose publicly.

How to use it:
- Import from `harnessiq/tools/leadiq` when you want the supported facade
  instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/tools/leadiq` explicit, discoverable,
  and easier to maintain.
===============================================================================
"""

from harnessiq.tools.leadiq.operations import (
    build_leadiq_request_tool_definition,
    create_leadiq_tools,
)

__all__ = [
    "build_leadiq_request_tool_definition",
    "create_leadiq_tools",
]
