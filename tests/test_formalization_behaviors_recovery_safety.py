from __future__ import annotations

import unittest

from harnessiq.formalization import (
    ErrorEscalationBehavior,
    IrreversibleActionGateBehavior,
    RateLimitBehavior,
    RetryStrategyBehavior,
    ScopeGuardBehavior,
    StuckDetectionBehavior,
)
from harnessiq.shared.agents import AgentPauseSignal
from harnessiq.shared.tools import ToolCall, ToolResult


class RecoveryBehaviorTests(unittest.TestCase):
    def test_retry_strategy_behavior_blocks_same_failing_call_after_limit(self) -> None:
        layer = RetryStrategyBehavior(monitored_patterns=("exa.*",), max_retries=2)
        first_call = ToolCall(tool_key="exa.request", arguments={"query": "acme"})
        different_call = ToolCall(tool_key="exa.request", arguments={"query": "globex"})

        self.assertIs(layer.on_tool_call(first_call), first_call)
        layer.on_tool_result_event(first_call, ToolResult(tool_key="exa.request", output={"error": "boom-1"}))

        self.assertIs(layer.on_tool_call(first_call), first_call)
        layer.on_tool_result_event(first_call, ToolResult(tool_key="exa.request", output={"error": "boom-2"}))

        blocked = layer.on_tool_call(first_call)
        self.assertIsInstance(blocked, ToolResult)
        assert isinstance(blocked, ToolResult)
        self.assertIn("Retry limit reached", blocked.output["error"])

        self.assertIs(layer.on_tool_call(different_call), different_call)

    def test_stuck_detection_behavior_blocks_after_repeated_identical_calls(self) -> None:
        layer = StuckDetectionBehavior(threshold=2, monitored_patterns=("artifact.*",))
        repeated_call = ToolCall(tool_key="artifact.write_json", arguments={"name": "memo"})
        changed_call = ToolCall(tool_key="artifact.write_json", arguments={"name": "summary"})

        self.assertIs(layer.on_tool_call(repeated_call), repeated_call)
        self.assertIs(layer.on_tool_call(repeated_call), repeated_call)

        blocked = layer.on_tool_call(repeated_call)
        self.assertIsInstance(blocked, ToolResult)
        assert isinstance(blocked, ToolResult)
        self.assertIn("Stuck pattern detected", blocked.output["error"])

        self.assertIs(layer.on_tool_call(changed_call), changed_call)

    def test_error_escalation_behavior_pauses_after_consecutive_failures(self) -> None:
        layer = ErrorEscalationBehavior(monitored_patterns=("browser.*",), max_consecutive_failures=2)
        first_call = ToolCall(tool_key="browser.navigate", arguments={"url": "https://example.test"})
        second_call = ToolCall(tool_key="browser.click", arguments={"selector": "#submit"})

        layer.on_tool_result_event(first_call, ToolResult(tool_key="browser.navigate", output={"error": "network"}))
        layer.on_tool_result_event(second_call, ToolResult(tool_key="browser.click", output={"error": "timeout"}))

        pause_signal = layer.on_tool_call(first_call)
        self.assertIsInstance(pause_signal, AgentPauseSignal)
        assert isinstance(pause_signal, AgentPauseSignal)
        self.assertIn("Error escalation triggered", pause_signal.reason)


class SafetyBehaviorTests(unittest.TestCase):
    def test_irreversible_action_gate_requires_confirmation_and_consumes_it(self) -> None:
        layer = IrreversibleActionGateBehavior(irreversible_patterns=("filesystem.write_*",))
        write_call = ToolCall(
            tool_key="filesystem.write_text_file",
            arguments={"path": "memory/output.md", "content": "hello"},
        )

        visible_before = layer.filter_tool_keys(
            ("filesystem.write_text_file", "behavior.confirm_action", "filesystem.read_text_file")
        )
        self.assertEqual(visible_before, ("behavior.confirm_action", "filesystem.read_text_file"))

        blocked = layer.on_tool_call(write_call)
        self.assertIsInstance(blocked, ToolResult)

        confirm_tool = layer.get_formalization_tools()[0]
        confirmed = confirm_tool.execute(
            {
                "target_tool": "filesystem.write_text_file",
                "rationale": "Need to persist the final output.",
            }
        )
        self.assertTrue(confirmed.output["confirmed"])

        visible_after_confirm = layer.filter_tool_keys(
            ("filesystem.write_text_file", "behavior.confirm_action", "filesystem.read_text_file")
        )
        self.assertEqual(
            visible_after_confirm,
            ("filesystem.write_text_file", "behavior.confirm_action", "filesystem.read_text_file"),
        )

        layer.on_tool_result_event(write_call, ToolResult(tool_key="filesystem.write_text_file", output={"ok": True}))
        visible_after_use = layer.filter_tool_keys(
            ("filesystem.write_text_file", "behavior.confirm_action", "filesystem.read_text_file")
        )
        self.assertEqual(visible_after_use, ("behavior.confirm_action", "filesystem.read_text_file"))

    def test_rate_limit_behavior_hides_tools_during_cooldown_and_after_limit(self) -> None:
        layer = RateLimitBehavior(limits={"instantly.*": 2}, window="reset", cooldown_cycles=1)
        layer.on_agent_prepare(agent_name="demo", memory_path="memory/demo")

        layer.on_tool_result(ToolResult(tool_key="instantly.pause_campaign", output={"ok": True}))
        visible_during_cooldown = layer.filter_tool_keys(("instantly.pause_campaign", "serper.request"))
        self.assertEqual(visible_during_cooldown, ("serper.request",))

        layer.on_tool_result(ToolResult(tool_key="serper.request", output={"ok": True}))
        visible_after_cooldown = layer.filter_tool_keys(("instantly.pause_campaign", "serper.request"))
        self.assertEqual(visible_after_cooldown, ("instantly.pause_campaign", "serper.request"))

        layer.on_tool_result(ToolResult(tool_key="instantly.resume_campaign", output={"ok": True}))
        limited = layer.filter_tool_keys(("instantly.pause_campaign", "instantly.resume_campaign", "serper.request"))
        self.assertEqual(limited, ("serper.request",))

    def test_scope_guard_behavior_blocks_out_of_scope_arguments(self) -> None:
        layer = ScopeGuardBehavior(
            guarded_patterns=("filesystem.write_*",),
            argument_block_patterns=(("path", "..\\"), ("path", "C:\\Windows")),
        )
        blocked_call = ToolCall(
            tool_key="filesystem.write_text_file",
            arguments={"path": "..\\outside.txt", "content": "unsafe"},
        )
        safe_call = ToolCall(
            tool_key="filesystem.write_text_file",
            arguments={"path": "memory\\safe.txt", "content": "ok"},
        )

        blocked = layer.on_tool_call(blocked_call)
        self.assertIsInstance(blocked, ToolResult)
        assert isinstance(blocked, ToolResult)
        self.assertIn("forbidden scope value", blocked.output["error"])

        self.assertIs(layer.on_tool_call(safe_call), safe_call)


if __name__ == "__main__":
    unittest.main()
