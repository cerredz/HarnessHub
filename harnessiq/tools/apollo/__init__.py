"""
===============================================================================
File: harnessiq/tools/apollo/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/tools/apollo` within
  the HarnessIQ runtime.
- Apollo MCP-style tool factory.

Use cases:
- Import build_apollo_request_tool_definition, create_apollo_tools from one
  stable package entry point.
- Read this module to understand what `harnessiq/tools/apollo` intends to
  expose publicly.

How to use it:
- Import from `harnessiq/tools/apollo` when you want the supported facade
  instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/tools/apollo` explicit, discoverable,
  and easier to maintain.
===============================================================================
"""

from harnessiq.tools.apollo.operations import (
    build_apollo_request_tool_definition,
    create_apollo_tools,
)

__all__ = [
    "build_apollo_request_tool_definition",
    "create_apollo_tools",
]
