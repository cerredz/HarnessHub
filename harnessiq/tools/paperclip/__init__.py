"""
===============================================================================
File: harnessiq/tools/paperclip/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/tools/paperclip`
  within the HarnessIQ runtime.
- Paperclip tool registration for the Harnessiq tool layer.

Use cases:
- Import build_paperclip_request_tool_definition, create_paperclip_tools from
  one stable package entry point.
- Read this module to understand what `harnessiq/tools/paperclip` intends to
  expose publicly.

How to use it:
- Import from `harnessiq/tools/paperclip` when you want the supported facade
  instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/tools/paperclip` explicit,
  discoverable, and easier to maintain.
===============================================================================
"""

from harnessiq.tools.paperclip.operations import (
    build_paperclip_request_tool_definition,
    create_paperclip_tools,
)

__all__ = [
    "build_paperclip_request_tool_definition",
    "create_paperclip_tools",
]
