"""
===============================================================================
File: harnessiq/agents/spawn_specialized_subagents/__init__.py

What this file does:
- Defines the package-level export surface for
  `harnessiq/agents/spawn_specialized_subagents` within the HarnessIQ runtime.
- Spawn-specialized-subagents harness package.

Use cases:
- Import SpawnSpecializedSubagentsAgent from one stable package entry point.
- Read this module to understand what
  `harnessiq/agents/spawn_specialized_subagents` intends to expose publicly.

How to use it:
- Import from `harnessiq/agents/spawn_specialized_subagents` when you want the
  supported facade instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/agents/spawn_specialized_subagents`
  explicit, discoverable, and easier to maintain.
===============================================================================
"""

from .agent import SpawnSpecializedSubagentsAgent

__all__ = ["SpawnSpecializedSubagentsAgent"]
