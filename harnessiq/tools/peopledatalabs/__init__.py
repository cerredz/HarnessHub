"""
===============================================================================
File: harnessiq/tools/peopledatalabs/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/tools/peopledatalabs`
  within the HarnessIQ runtime.
- People Data Labs MCP-style tool factory.

Use cases:
- Import build_peopledatalabs_request_tool_definition,
  create_peopledatalabs_tools from one stable package entry point.
- Read this module to understand what `harnessiq/tools/peopledatalabs` intends
  to expose publicly.

How to use it:
- Import from `harnessiq/tools/peopledatalabs` when you want the supported
  facade instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/tools/peopledatalabs` explicit,
  discoverable, and easier to maintain.
===============================================================================
"""

from harnessiq.tools.peopledatalabs.operations import (
    build_peopledatalabs_request_tool_definition,
    create_peopledatalabs_tools,
)

__all__ = [
    "build_peopledatalabs_request_tool_definition",
    "create_peopledatalabs_tools",
]
