"""
===============================================================================
File: harnessiq/tools/eval/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/tools/eval` within
  the HarnessIQ runtime.
- Shared evaluation tool factories.

Use cases:
- Import build_evaluate_company_tool_definition, create_evaluate_company_tool
  from one stable package entry point.
- Read this module to understand what `harnessiq/tools/eval` intends to expose
  publicly.

How to use it:
- Import from `harnessiq/tools/eval` when you want the supported facade instead
  of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/tools/eval` explicit, discoverable,
  and easier to maintain.
===============================================================================
"""

from .evaluate_company import (
    build_evaluate_company_tool_definition,
    create_evaluate_company_tool,
)

__all__ = [
    "build_evaluate_company_tool_definition",
    "create_evaluate_company_tool",
]
