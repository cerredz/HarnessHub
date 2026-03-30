"""
===============================================================================
File: harnessiq/tools/spawn_specialized_subagents/__init__.py

What this file does:
- Defines the package-level export surface for
  `harnessiq/tools/spawn_specialized_subagents` within the HarnessIQ runtime.
- Spawn-specialized-subagents harness tool factories.

Use cases:
- Import build_integrate_results_tool_definition,
  build_plan_assignments_tool_definition, build_run_assignment_tool_definition,
  create_spawn_specialized_subagents_tools from one stable package entry point.
- Read this module to understand what
  `harnessiq/tools/spawn_specialized_subagents` intends to expose publicly.

How to use it:
- Import from `harnessiq/tools/spawn_specialized_subagents` when you want the
  supported facade instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/tools/spawn_specialized_subagents`
  explicit, discoverable, and easier to maintain.
===============================================================================
"""

from .operations import (
    build_integrate_results_tool_definition,
    build_plan_assignments_tool_definition,
    build_run_assignment_tool_definition,
    create_spawn_specialized_subagents_tools,
)

__all__ = [
    "build_integrate_results_tool_definition",
    "build_plan_assignments_tool_definition",
    "build_run_assignment_tool_definition",
    "create_spawn_specialized_subagents_tools",
]
