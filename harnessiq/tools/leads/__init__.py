"""
===============================================================================
File: harnessiq/tools/leads/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/tools/leads` within
  the HarnessIQ runtime.
- Leads agent tool factories.

Use cases:
- Import create_leads_tools from one stable package entry point.
- Read this module to understand what `harnessiq/tools/leads` intends to expose
  publicly.

How to use it:
- Import from `harnessiq/tools/leads` when you want the supported facade
  instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/tools/leads` explicit, discoverable,
  and easier to maintain.
===============================================================================
"""

from .operations import create_leads_tools

__all__ = ["create_leads_tools"]
