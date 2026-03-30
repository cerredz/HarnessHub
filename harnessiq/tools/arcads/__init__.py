"""
===============================================================================
File: harnessiq/tools/arcads/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/tools/arcads` within
  the HarnessIQ runtime.
- Arcads tool registration for the Harnessiq tool layer.

Use cases:
- Import build_arcads_request_tool_definition, create_arcads_tools from one
  stable package entry point.
- Read this module to understand what `harnessiq/tools/arcads` intends to
  expose publicly.

How to use it:
- Import from `harnessiq/tools/arcads` when you want the supported facade
  instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/tools/arcads` explicit, discoverable,
  and easier to maintain.
===============================================================================
"""

from harnessiq.tools.arcads.operations import (
    build_arcads_request_tool_definition,
    create_arcads_tools,
)

__all__ = [
    "build_arcads_request_tool_definition",
    "create_arcads_tools",
]
