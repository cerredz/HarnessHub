from __future__ import annotations

from harnessiq.shared.tools import ToolResult
from harnessiq.tools import (
    HookContext,
    HookResponse,
    RegisteredHook,
    create_default_hook_tools,
    define_hook_tool,
    hook_tool,
    is_tool_allowed,
)


def test_define_hook_tool_returns_registered_hook_with_default_name() -> None:
    hook = define_hook_tool(
        key="hooks.audit.before_tool",
        description="Record one before-tool lifecycle event.",
        phases=("before_tool",),
        handler=lambda context: HookResponse(),
    )

    assert isinstance(hook, RegisteredHook)
    assert hook.key == "hooks.audit.before_tool"
    assert hook.definition.name == "before_tool"
    assert hook.definition.phases == ("before_tool",)


def test_hook_tool_decorator_builds_executable_registered_hook() -> None:
    @hook_tool(
        key="hooks.audit.after_tool",
        description="Record one after-tool lifecycle event.",
        phases=("after_tool",),
    )
    def audit(context: HookContext) -> HookResponse:
        return HookResponse(
            tool_result=ToolResult(
                tool_key=context.tool_key or "unknown.tool",
                output={"phase": context.phase},
            )
        )

    result = audit.execute(
        HookContext(
            phase="after_tool",
            agent_name="inspectable",
            run_id="run-123",
            cycle_index=1,
            reset_count=0,
            tool_key="session.echo",
        )
    )

    assert result is not None
    assert result.tool_result is not None
    assert result.tool_result.output == {"phase": "after_tool"}


def test_create_default_hook_tools_returns_policy_gate_when_policy_is_enabled() -> None:
    hooks = create_default_hook_tools(approval_policy="on-request")

    assert [hook.key for hook in hooks] == ["hooks.approval_gate"]


def test_is_tool_allowed_supports_family_exact_and_prefix_patterns() -> None:
    allowed_tools = (
        "filesystem",
        "context.select.*",
        "text.normalize_whitespace",
        "reasoning.step*",
    )

    assert is_tool_allowed("filesystem.read_text_file", allowed_tools) is True
    assert is_tool_allowed("context.select.checkpoint", allowed_tools) is True
    assert is_tool_allowed("text.normalize_whitespace", allowed_tools) is True
    assert is_tool_allowed("reasoning.step_by_step", allowed_tools) is True
    assert is_tool_allowed("reason.brainstorm", allowed_tools) is False
