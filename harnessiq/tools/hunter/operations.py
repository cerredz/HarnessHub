"""
===============================================================================
File: harnessiq/tools/hunter/operations.py

What this file does:
- Exposes the `hunter` tool family for the HarnessIQ tool layer.
- In most packages this module is the bridge between provider-backed operations
  and the generic tool registration surface.
- Hunter MCP-style tool factory for the Harnessiq tool layer.

Use cases:
- Import this module when an agent or registry needs the `hunter` tool
  definitions.
- Read it to see which runtime operations are intentionally surfaced as tools.

How to use it:
- Call the exported factory helpers from `harnessiq/tools/hunter` and merge the
  resulting tools into a registry.

Intent:
- Keep the public `hunter` tool surface small, explicit, and separate from
  provider implementation details.
===============================================================================
"""

from harnessiq.providers.hunter.operations import (
    build_hunter_request_tool_definition,
    create_hunter_tools,
)

__all__ = [
    "build_hunter_request_tool_definition",
    "create_hunter_tools",
]
