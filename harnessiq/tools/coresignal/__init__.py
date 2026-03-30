"""
===============================================================================
File: harnessiq/tools/coresignal/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/tools/coresignal`
  within the HarnessIQ runtime.
- Coresignal MCP-style tool factory.

Use cases:
- Import build_coresignal_request_tool_definition, create_coresignal_tools from
  one stable package entry point.
- Read this module to understand what `harnessiq/tools/coresignal` intends to
  expose publicly.

How to use it:
- Import from `harnessiq/tools/coresignal` when you want the supported facade
  instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/tools/coresignal` explicit,
  discoverable, and easier to maintain.
===============================================================================
"""

from harnessiq.tools.coresignal.operations import (
    build_coresignal_request_tool_definition,
    create_coresignal_tools,
)

__all__ = [
    "build_coresignal_request_tool_definition",
    "create_coresignal_tools",
]
