"""
===============================================================================
File: harnessiq/tools/context/injection.py

What this file does:
- Implements part of the context-tool system that rewrites, summarizes, or
  annotates an agent context window.
- Compatibility wrapper for transcript injection tool definitions.

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

from .definitions.injection import create_context_injection_tools

__all__ = ["create_context_injection_tools"]
