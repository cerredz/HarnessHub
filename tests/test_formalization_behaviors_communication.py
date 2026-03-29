from __future__ import annotations

import tempfile
import unittest

from harnessiq.formalization import (
    DecisionLoggingBehavior,
    ProgressReportingBehavior,
    UncertaintySignalingBehavior,
)
from harnessiq.shared.tools import CONTROL_EMIT_DECISION, ToolCall, ToolResult
from harnessiq.tools.control import create_control_tools


def _emit_decision_result(root: str) -> ToolResult:
    tool = next(
        tool
        for tool in create_control_tools(root=root)
        if tool.key == CONTROL_EMIT_DECISION
    )
    return tool.execute(
        {
            "decision_id": "log-1",
            "chosen": "write-report",
            "rationale": "The prerequisites are satisfied.",
        }
    )


class CommunicationBehaviorTests(unittest.TestCase):
    def test_progress_reporting_behavior_blocks_after_cycle_threshold_until_reported(self) -> None:
        layer = ProgressReportingBehavior(
            every_n_cycles=2,
            blocked_patterns=("artifact.*",),
        )

        initial = layer.filter_tool_keys(("artifact.write_json", ProgressReportingBehavior.REPORT_TOOL_KEY))
        self.assertEqual(initial, ("artifact.write_json", ProgressReportingBehavior.REPORT_TOOL_KEY))

        layer.on_tool_result(ToolResult(tool_key="search.web", output={"ok": True}))
        after_one_cycle = layer.filter_tool_keys(("artifact.write_json", ProgressReportingBehavior.REPORT_TOOL_KEY))
        self.assertEqual(after_one_cycle, ("artifact.write_json", ProgressReportingBehavior.REPORT_TOOL_KEY))

        layer.on_tool_result(ToolResult(tool_key="search.web", output={"ok": True}))
        blocked = layer.filter_tool_keys(("artifact.write_json", ProgressReportingBehavior.REPORT_TOOL_KEY))
        self.assertEqual(blocked, (ProgressReportingBehavior.REPORT_TOOL_KEY,))

        report_tool = layer.get_formalization_tools()[0]
        report_result = report_tool.execute({"summary": "Progress update", "next_steps": ["Finish the report"]})
        layer.on_tool_result(report_result)

        unblocked = layer.filter_tool_keys(("artifact.write_json", ProgressReportingBehavior.REPORT_TOOL_KEY))
        self.assertEqual(unblocked, ("artifact.write_json", ProgressReportingBehavior.REPORT_TOOL_KEY))

    def test_progress_reporting_behavior_blocks_after_reset_threshold(self) -> None:
        layer = ProgressReportingBehavior(
            every_n_resets=1,
            blocked_patterns=("control.mark_complete",),
        )

        layer.on_post_reset()
        blocked = layer.filter_tool_keys(("control.mark_complete", ProgressReportingBehavior.REPORT_TOOL_KEY))
        self.assertEqual(blocked, (ProgressReportingBehavior.REPORT_TOOL_KEY,))

        report_tool = layer.get_formalization_tools()[0]
        layer.on_tool_result(report_tool.execute({"summary": "Recovered after reset"}))

        unblocked = layer.filter_tool_keys(("control.mark_complete", ProgressReportingBehavior.REPORT_TOOL_KEY))
        self.assertEqual(unblocked, ("control.mark_complete", ProgressReportingBehavior.REPORT_TOOL_KEY))

    def test_decision_logging_behavior_requires_emit_decision_before_action(self) -> None:
        layer = DecisionLoggingBehavior(target_patterns=("artifact.write_*",))

        visible_before = layer.filter_tool_keys(("artifact.write_json", CONTROL_EMIT_DECISION))
        self.assertEqual(visible_before, (CONTROL_EMIT_DECISION,))

        with tempfile.TemporaryDirectory() as temp_dir:
            decision_result = _emit_decision_result(temp_dir)
        layer.on_tool_result(decision_result)

        visible_after_decision = layer.filter_tool_keys(("artifact.write_json", CONTROL_EMIT_DECISION))
        self.assertEqual(visible_after_decision, ("artifact.write_json", CONTROL_EMIT_DECISION))

        layer.on_tool_result(ToolResult(tool_key="artifact.write_json", output={"ok": True}))
        visible_after_write = layer.filter_tool_keys(("artifact.write_json", CONTROL_EMIT_DECISION))
        self.assertEqual(visible_after_write, (CONTROL_EMIT_DECISION,))

    def test_uncertainty_signaling_behavior_requires_signal_after_empty_result(self) -> None:
        layer = UncertaintySignalingBehavior(
            monitored_patterns=("exa.*",),
            blocked_patterns=("artifact.*", "control.mark_complete"),
        )

        tool_call = ToolCall(tool_key="exa.request", arguments={"query": "acme"})
        result = ToolResult(tool_key="exa.request", output={"results": []})
        layer.on_tool_result_event(tool_call, result)

        blocked = layer.filter_tool_keys(
            ("artifact.write_json", "control.mark_complete", UncertaintySignalingBehavior.SIGNAL_TOOL_KEY)
        )
        self.assertEqual(blocked, (UncertaintySignalingBehavior.SIGNAL_TOOL_KEY,))

        signal_tool = layer.get_formalization_tools()[0]
        signal_result = signal_tool.execute(
            {
                "reason": "No matching records returned.",
                "observed_tool": "exa.request",
                "next_step": "Try a broader search query.",
            }
        )
        layer.on_tool_result(signal_result)

        unblocked = layer.filter_tool_keys(
            ("artifact.write_json", "control.mark_complete", UncertaintySignalingBehavior.SIGNAL_TOOL_KEY)
        )
        self.assertEqual(
            unblocked,
            ("artifact.write_json", "control.mark_complete", UncertaintySignalingBehavior.SIGNAL_TOOL_KEY),
        )


if __name__ == "__main__":
    unittest.main()
