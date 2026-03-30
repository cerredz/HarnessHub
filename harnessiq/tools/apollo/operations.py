"""
===============================================================================
File: harnessiq/tools/apollo/operations.py

What this file does:
- Exposes the `apollo` tool family for the HarnessIQ tool layer.
- In most packages this module is the bridge between provider-backed operations
  and the generic tool registration surface.
- Apollo MCP-style tool factory for the Harnessiq tool layer.

Use cases:
- Import this module when an agent or registry needs the `apollo` tool
  definitions.
- Read it to see which runtime operations are intentionally surfaced as tools.

How to use it:
- Call the exported factory helpers from `harnessiq/tools/apollo` and merge the
  resulting tools into a registry.

Intent:
- Keep the public `apollo` tool surface small, explicit, and separate from
  provider implementation details.
===============================================================================
"""

from harnessiq.providers.apollo.operations import (
    build_apollo_request_tool_definition,
    create_apollo_tools,
)

__all__ = [
    "build_apollo_request_tool_definition",
    "create_apollo_tools",
]
