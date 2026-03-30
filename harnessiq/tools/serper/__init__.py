"""
===============================================================================
File: harnessiq/tools/serper/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/tools/serper` within
  the HarnessIQ runtime.
- Serper tool registration for the Harnessiq tool layer.

Use cases:
- Import build_serper_request_tool_definition, create_serper_tools from one
  stable package entry point.
- Read this module to understand what `harnessiq/tools/serper` intends to
  expose publicly.

How to use it:
- Import from `harnessiq/tools/serper` when you want the supported facade
  instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/tools/serper` explicit, discoverable,
  and easier to maintain.
===============================================================================
"""

from harnessiq.tools.serper.operations import (
    build_serper_request_tool_definition,
    create_serper_tools,
)

__all__ = [
    "build_serper_request_tool_definition",
    "create_serper_tools",
]
