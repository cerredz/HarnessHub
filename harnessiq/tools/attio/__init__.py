"""
===============================================================================
File: harnessiq/tools/attio/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/tools/attio` within
  the HarnessIQ runtime.
- Attio tool registration for the Harnessiq tool layer.

Use cases:
- Import build_attio_request_tool_definition, create_attio_tools from one
  stable package entry point.
- Read this module to understand what `harnessiq/tools/attio` intends to expose
  publicly.

How to use it:
- Import from `harnessiq/tools/attio` when you want the supported facade
  instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/tools/attio` explicit, discoverable,
  and easier to maintain.
===============================================================================
"""

from harnessiq.tools.attio.operations import (
    build_attio_request_tool_definition,
    create_attio_tools,
)

__all__ = [
    "build_attio_request_tool_definition",
    "create_attio_tools",
]
