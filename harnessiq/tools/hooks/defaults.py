"""Default lifecycle hooks and policy helpers."""

from __future__ import annotations

from collections.abc import Sequence

from harnessiq.shared.hooks import ApprovalPolicy, DEFAULT_APPROVAL_POLICY, HookContext, HookResponse, RegisteredHook
from harnessiq.shared.tools import ToolResult

from .factory import define_hook_tool


def create_default_hook_tools(
    *,
    approval_policy: ApprovalPolicy = DEFAULT_APPROVAL_POLICY,
    allowed_tools: Sequence[str] = (),
) -> tuple[RegisteredHook, ...]:
    """Return the default policy hooks implied by runtime config."""
    normalized_allowed_tools = _normalize_allowed_tools(allowed_tools)
    if approval_policy == "never" and not normalized_allowed_tools:
        return ()
    return (
        create_approval_policy_hook(
            approval_policy=approval_policy,
            allowed_tools=normalized_allowed_tools,
        ),
    )


def create_approval_policy_hook(
    *,
    approval_policy: ApprovalPolicy = DEFAULT_APPROVAL_POLICY,
    allowed_tools: Sequence[str] = (),
) -> RegisteredHook:
    """Return the built-in before-tool approval/allowlist gate."""
    normalized_allowed_tools = _normalize_allowed_tools(allowed_tools)

    def handler(context: HookContext) -> HookResponse | None:
        if context.tool_key is None:
            return None
        is_allowed = is_tool_allowed(context.tool_key, normalized_allowed_tools)
        if approval_policy == "always":
            return _pause_for_approval(
                context=context,
                approval_policy=approval_policy,
                allowed_tools=normalized_allowed_tools,
            )
        if approval_policy == "on-request":
            if normalized_allowed_tools and is_allowed:
                return None
            return _pause_for_approval(
                context=context,
                approval_policy=approval_policy,
                allowed_tools=normalized_allowed_tools,
            )
        if normalized_allowed_tools and not is_allowed:
            return HookResponse(
                tool_result=ToolResult(
                    tool_key=context.tool_key,
                    output={
                        "error": (
                            f"Tool '{context.tool_key}' is not allowed by the current allowed_tools policy."
                        ),
                        "policy": {
                            "allowed_tools": list(normalized_allowed_tools),
                            "approval_policy": approval_policy,
                        },
                    },
                )
            )
        return None

    return define_hook_tool(
        key="hooks.approval_gate",
        description="Apply approval-policy and allowed-tools gates before executing a runtime tool call.",
        phases=("before_tool",),
        handler=handler,
        priority=10,
    )


def is_tool_allowed(tool_key: str, allowed_tools: Sequence[str]) -> bool:
    """Return whether a tool key matches any allowlist pattern."""
    normalized_allowed_tools = _normalize_allowed_tools(allowed_tools)
    if not normalized_allowed_tools:
        return False
    return any(_pattern_matches(tool_key, pattern) for pattern in normalized_allowed_tools)


def _pause_for_approval(
    *,
    context: HookContext,
    approval_policy: ApprovalPolicy,
    allowed_tools: Sequence[str],
) -> HookResponse:
    return HookResponse(
        pause_reason="approval required",
        pause_details={
            "agent_name": context.agent_name,
            "approval_policy": approval_policy,
            "allowed_tools": list(allowed_tools),
            "tool_arguments": dict(context.tool_arguments or {}),
            "tool_key": context.tool_key,
            "tool_name": context.tool_name,
        },
    )


def _normalize_allowed_tools(allowed_tools: Sequence[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for pattern in allowed_tools:
        candidate = str(pattern).strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        normalized.append(candidate)
    return tuple(normalized)


def _pattern_matches(tool_key: str, pattern: str) -> bool:
    normalized_pattern = pattern.strip()
    if not normalized_pattern:
        return False
    if normalized_pattern.endswith(".*"):
        return tool_key.startswith(normalized_pattern[:-1])
    if "*" in normalized_pattern:
        prefix = normalized_pattern.split("*", 1)[0]
        return tool_key.startswith(prefix)
    if "." not in normalized_pattern:
        return tool_key == normalized_pattern or tool_key.startswith(f"{normalized_pattern}.")
    return tool_key == normalized_pattern


__all__ = [
    "create_approval_policy_hook",
    "create_default_hook_tools",
    "is_tool_allowed",
]
