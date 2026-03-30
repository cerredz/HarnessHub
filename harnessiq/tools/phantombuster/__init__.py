"""
===============================================================================
File: harnessiq/tools/phantombuster/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/tools/phantombuster`
  within the HarnessIQ runtime.
- PhantomBuster MCP-style tool factory.

Use cases:
- Import build_phantombuster_request_tool_definition,
  create_phantombuster_tools from one stable package entry point.
- Read this module to understand what `harnessiq/tools/phantombuster` intends
  to expose publicly.

How to use it:
- Import from `harnessiq/tools/phantombuster` when you want the supported
  facade instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/tools/phantombuster` explicit,
  discoverable, and easier to maintain.
===============================================================================
"""

from harnessiq.tools.phantombuster.operations import (
    build_phantombuster_request_tool_definition,
    create_phantombuster_tools,
)

__all__ = [
    "build_phantombuster_request_tool_definition",
    "create_phantombuster_tools",
]
