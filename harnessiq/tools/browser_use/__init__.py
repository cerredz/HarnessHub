"""
===============================================================================
File: harnessiq/tools/browser_use/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/tools/browser_use`
  within the HarnessIQ runtime.
- Browser Use MCP-style tool factory.

Use cases:
- Import build_browser_use_request_tool_definition, create_browser_use_tools
  from one stable package entry point.
- Read this module to understand what `harnessiq/tools/browser_use` intends to
  expose publicly.

How to use it:
- Import from `harnessiq/tools/browser_use` when you want the supported facade
  instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/tools/browser_use` explicit,
  discoverable, and easier to maintain.
===============================================================================
"""

from harnessiq.tools.browser_use.operations import (
    build_browser_use_request_tool_definition,
    create_browser_use_tools,
)

__all__ = [
    "build_browser_use_request_tool_definition",
    "create_browser_use_tools",
]
