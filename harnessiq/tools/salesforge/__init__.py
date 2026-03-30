"""
===============================================================================
File: harnessiq/tools/salesforge/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/tools/salesforge`
  within the HarnessIQ runtime.
- Salesforge MCP-style tool factory.

Use cases:
- Import build_salesforge_request_tool_definition, create_salesforge_tools from
  one stable package entry point.
- Read this module to understand what `harnessiq/tools/salesforge` intends to
  expose publicly.

How to use it:
- Import from `harnessiq/tools/salesforge` when you want the supported facade
  instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/tools/salesforge` explicit,
  discoverable, and easier to maintain.
===============================================================================
"""

from harnessiq.tools.salesforge.operations import (
    build_salesforge_request_tool_definition,
    create_salesforge_tools,
)

__all__ = [
    "build_salesforge_request_tool_definition",
    "create_salesforge_tools",
]
