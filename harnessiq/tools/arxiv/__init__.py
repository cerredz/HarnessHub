"""
===============================================================================
File: harnessiq/tools/arxiv/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/tools/arxiv` within
  the HarnessIQ runtime.
- arXiv MCP-style tool factory.

Use cases:
- Import build_arxiv_request_tool_definition, create_arxiv_tools from one
  stable package entry point.
- Read this module to understand what `harnessiq/tools/arxiv` intends to expose
  publicly.

How to use it:
- Import from `harnessiq/tools/arxiv` when you want the supported facade
  instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/tools/arxiv` explicit, discoverable,
  and easier to maintain.
===============================================================================
"""

from .operations import build_arxiv_request_tool_definition, create_arxiv_tools

__all__ = [
    "build_arxiv_request_tool_definition",
    "create_arxiv_tools",
]
