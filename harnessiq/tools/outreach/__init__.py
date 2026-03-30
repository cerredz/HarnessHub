"""
===============================================================================
File: harnessiq/tools/outreach/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/tools/outreach`
  within the HarnessIQ runtime.
- Outreach tool registration for the Harnessiq tool layer.

Use cases:
- Import build_outreach_request_tool_definition, create_outreach_tools from one
  stable package entry point.
- Read this module to understand what `harnessiq/tools/outreach` intends to
  expose publicly.

How to use it:
- Import from `harnessiq/tools/outreach` when you want the supported facade
  instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/tools/outreach` explicit,
  discoverable, and easier to maintain.
===============================================================================
"""

from harnessiq.tools.outreach.operations import (
    build_outreach_request_tool_definition,
    create_outreach_tools,
)

__all__ = [
    "build_outreach_request_tool_definition",
    "create_outreach_tools",
]
