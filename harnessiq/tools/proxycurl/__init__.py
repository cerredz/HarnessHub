"""
===============================================================================
File: harnessiq/tools/proxycurl/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/tools/proxycurl`
  within the HarnessIQ runtime.
- Proxycurl MCP-style tool factory. NOTE: Proxycurl shut down in January 2025
  following a LinkedIn lawsuit. This package is preserved for reference only.

Use cases:
- Import build_proxycurl_request_tool_definition, create_proxycurl_tools from
  one stable package entry point.
- Read this module to understand what `harnessiq/tools/proxycurl` intends to
  expose publicly.

How to use it:
- Import from `harnessiq/tools/proxycurl` when you want the supported facade
  instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/tools/proxycurl` explicit,
  discoverable, and easier to maintain.
===============================================================================
"""

from harnessiq.tools.proxycurl.operations import (
    build_proxycurl_request_tool_definition,
    create_proxycurl_tools,
)

__all__ = [
    "build_proxycurl_request_tool_definition",
    "create_proxycurl_tools",
]
