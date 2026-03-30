"""
===============================================================================
File: harnessiq/tools/inboxapp/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/tools/inboxapp`
  within the HarnessIQ runtime.
- InboxApp tool registration for the Harnessiq tool layer.

Use cases:
- Import build_inboxapp_request_tool_definition, create_inboxapp_tools from one
  stable package entry point.
- Read this module to understand what `harnessiq/tools/inboxapp` intends to
  expose publicly.

How to use it:
- Import from `harnessiq/tools/inboxapp` when you want the supported facade
  instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/tools/inboxapp` explicit,
  discoverable, and easier to maintain.
===============================================================================
"""

from harnessiq.tools.inboxapp.operations import (
    build_inboxapp_request_tool_definition,
    create_inboxapp_tools,
)

__all__ = [
    "build_inboxapp_request_tool_definition",
    "create_inboxapp_tools",
]
