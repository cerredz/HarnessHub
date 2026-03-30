"""
===============================================================================
File: harnessiq/tools/hooks/__init__.py

What this file does:
- Defines the package-level export surface for `harnessiq/tools/hooks` within
  the HarnessIQ runtime.
- Runtime hook factories and default policy helpers.

Use cases:
- Import ApprovalPolicy, DEFAULT_APPROVAL_POLICY, HookContext, HookDefinition,
  HookHandler, HookPhase from one stable package entry point.
- Read this module to understand what `harnessiq/tools/hooks` intends to expose
  publicly.

How to use it:
- Import from `harnessiq/tools/hooks` when you want the supported facade
  instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/tools/hooks` explicit, discoverable,
  and easier to maintain.
===============================================================================
"""

from harnessiq.shared.hooks import (
    ApprovalPolicy,
    DEFAULT_APPROVAL_POLICY,
    HookContext,
    HookDefinition,
    HookHandler,
    HookPhase,
    HookResponse,
    RegisteredHook,
)

from .defaults import create_approval_policy_hook, create_default_hook_tools, is_tool_allowed
from .factory import define_hook_tool, hook_tool

__all__ = [
    "ApprovalPolicy",
    "DEFAULT_APPROVAL_POLICY",
    "HookContext",
    "HookDefinition",
    "HookHandler",
    "HookPhase",
    "HookResponse",
    "RegisteredHook",
    "create_approval_policy_hook",
    "create_default_hook_tools",
    "define_hook_tool",
    "hook_tool",
    "is_tool_allowed",
]
