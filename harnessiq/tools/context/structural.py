"""
===============================================================================
File: harnessiq/tools/context/structural.py

What this file does:
- Implements part of the context-tool system that rewrites, summarizes, or
  annotates an agent context window.
- Compatibility wrapper for structural context tool definitions.

Use cases:
- Use these helpers when a runtime needs deterministic context compaction or
  injection behavior.

How to use it:
- Import the definitions or executors from this module through the context-tool
  catalog rather than wiring ad hoc context mutations inline.

Intent:
- Keep context-window manipulation explicit and reusable so long-running agents
  can manage token pressure predictably.
===============================================================================
"""

from .definitions.structural import create_context_structural_tools

__all__ = ["create_context_structural_tools"]
