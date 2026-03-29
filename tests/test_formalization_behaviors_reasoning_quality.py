from __future__ import annotations

import unittest

from harnessiq.formalization import (
    CitationRequirementBehavior,
    HypothesisTestingBehavior,
    PreActionReasoningBehavior,
    QualityCriterionSpec,
    QualityGateBehavior,
    ScopeEnforcementBehavior,
    SelfCritiqueBehavior,
)
from harnessiq.shared.tools import CONTROL_MARK_COMPLETE, ToolCall, ToolResult
from harnessiq.tools.control import create_control_tools


def _mark_complete_result(summary: str = "done") -> ToolResult:
    tool = next(tool for tool in create_control_tools(root="memory/test") if tool.key == CONTROL_MARK_COMPLETE)
    return tool.execute({"summary": summary})


class ReasoningBehaviorTests(unittest.TestCase):
    def test_pre_action_reasoning_behavior_requires_reasoning_before_action(self) -> None:
        layer = PreActionReasoningBehavior(
            before_patterns=("artifact.write_*",),
            reasoning_patterns=("reason.*",),
        )

        visible_before = layer.filter_tool_keys(("artifact.write_json", "reason.chain_of_thought"))
        self.assertEqual(visible_before, ("reason.chain_of_thought",))

        layer.on_tool_result(ToolResult(tool_key="reason.chain_of_thought", output={"ok": True}))
        visible_after_reasoning = layer.filter_tool_keys(("artifact.write_json", "reason.chain_of_thought"))
        self.assertEqual(visible_after_reasoning, ("artifact.write_json", "reason.chain_of_thought"))

        layer.on_tool_result(ToolResult(tool_key="artifact.write_json", output={"ok": True}))
        visible_after_write = layer.filter_tool_keys(("artifact.write_json", "reason.chain_of_thought"))
        self.assertEqual(visible_after_write, ("reason.chain_of_thought",))

    def test_self_critique_behavior_blocks_follow_up_actions_until_critique(self) -> None:
        layer = SelfCritiqueBehavior(
            output_patterns=("artifact.write_*",),
            blocked_until_critique=("artifact.*", "control.mark_complete"),
            critique_patterns=("reason.critique",),
        )

        layer.on_tool_result(ToolResult(tool_key="artifact.write_json", output={"ok": True}))
        visible_pending = layer.filter_tool_keys(
            ("artifact.write_json", "control.mark_complete", "reason.critique")
        )
        self.assertEqual(visible_pending, ("reason.critique",))

        layer.on_tool_result(ToolResult(tool_key="reason.critique", output={"ok": True}))
        visible_after_critique = layer.filter_tool_keys(
            ("artifact.write_json", "control.mark_complete", "reason.critique")
        )
        self.assertEqual(
            visible_after_critique,
            ("artifact.write_json", "control.mark_complete", "reason.critique"),
        )

    def test_hypothesis_testing_behavior_requires_generation_and_testing(self) -> None:
        layer = HypothesisTestingBehavior(
            commit_patterns=("control.mark_complete",),
            hypothesis_patterns=("reason.brainstorm",),
            testing_patterns=("reason.critique",),
        )

        visible_before = layer.filter_tool_keys(("control.mark_complete", "reason.brainstorm", "reason.critique"))
        self.assertEqual(visible_before, ("reason.brainstorm", "reason.critique"))

        layer.on_tool_result(ToolResult(tool_key="reason.brainstorm", output={"ok": True}))
        still_blocked = layer.filter_tool_keys(("control.mark_complete", "reason.brainstorm", "reason.critique"))
        self.assertEqual(still_blocked, ("reason.brainstorm", "reason.critique"))

        layer.on_tool_result(ToolResult(tool_key="reason.critique", output={"ok": True}))
        visible_after_testing = layer.filter_tool_keys(("control.mark_complete", "reason.brainstorm", "reason.critique"))
        self.assertEqual(
            visible_after_testing,
            ("control.mark_complete", "reason.brainstorm", "reason.critique"),
        )


class QualityBehaviorTests(unittest.TestCase):
    def test_scope_enforcement_behavior_records_violations_and_blocks_completion(self) -> None:
        layer = ScopeEnforcementBehavior(
            in_scope=("Researching sources",),
            out_of_scope=("Sending emails",),
        )

        flag_tool = layer.get_formalization_tools()[0]
        violation_result = flag_tool.execute({"topic": "Send an email", "reason": "Out of scope"})
        self.assertTrue(violation_result.output["recorded"])

        completion = layer.on_tool_result(_mark_complete_result())
        self.assertEqual(completion.tool_key, CONTROL_MARK_COMPLETE)
        self.assertIn("Completion blocked", completion.output["error"])

    def test_quality_gate_behavior_blocks_completion_until_evaluator_passes(self) -> None:
        state = {"ready": False}

        def evaluator(criterion: QualityCriterionSpec, agent_state: dict[str, object]) -> tuple[bool, str]:
            del criterion
            if agent_state["ready"]:
                return True, ""
            return False, "Quality flag is not ready."

        layer = QualityGateBehavior(
            criteria=(QualityCriterionSpec(criterion_id="READY_FLAG", description="Ready flag must be true."),),
            evaluator=evaluator,
            state_builder=lambda: dict(state),
        )

        blocked = layer.on_tool_result(_mark_complete_result())
        self.assertIn("READY_FLAG", blocked.output["failed_criteria"])

        state["ready"] = True
        allowed = layer.on_tool_result(_mark_complete_result())
        self.assertEqual(allowed.tool_key, CONTROL_MARK_COMPLETE)

    def test_citation_requirement_behavior_blocks_completion_when_records_lack_citations(self) -> None:
        layer = CitationRequirementBehavior(monitored_patterns=("artifact.write_json",))

        layer.on_tool_call(
            ToolCall(
                tool_key="artifact.write_json",
                arguments={"data": [{"title": "Example", "source_url": ""}]},
            )
        )
        visible_pending = layer.filter_tool_keys(("control.mark_complete", "artifact.write_json"))
        self.assertEqual(visible_pending, ("artifact.write_json",))

        blocked = layer.on_tool_result(_mark_complete_result())
        self.assertIn("CITATION_REQUIREMENTS", blocked.output["failed_criteria"])

        layer.on_tool_call(
            ToolCall(
                tool_key="artifact.write_json",
                arguments={"data": [{"title": "Example", "source_url": "https://example.test", "publication_date": "2026-03-29"}]},
            )
        )
        visible_after_fix = layer.filter_tool_keys(("control.mark_complete", "artifact.write_json"))
        self.assertEqual(visible_after_fix, ("control.mark_complete", "artifact.write_json"))


if __name__ == "__main__":
    unittest.main()
