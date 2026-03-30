"""
===============================================================================
File: harnessiq/tools/expandi/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/tools/expandi` within
  the HarnessIQ runtime.
- Expandi tool registration for the Harnessiq tool layer.

Use cases:
- Import build_expandi_request_tool_definition, create_expandi_tools from one
  stable package entry point.
- Read this module to understand what `harnessiq/tools/expandi` intends to
  expose publicly.

How to use it:
- Import from `harnessiq/tools/expandi` when you want the supported facade
  instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/tools/expandi` explicit, discoverable,
  and easier to maintain.
===============================================================================
"""

from harnessiq.tools.expandi.operations import (
    build_expandi_request_tool_definition,
    create_expandi_tools,
)

__all__ = [
    "build_expandi_request_tool_definition",
    "create_expandi_tools",
]
