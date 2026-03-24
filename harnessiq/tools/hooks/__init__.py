"""Runtime hook factories and default policy helpers."""

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
