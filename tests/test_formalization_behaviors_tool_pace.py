from __future__ import annotations

import unittest

from harnessiq.formalization import (
    ProgressCheckpointBehavior,
    ReflectionCadenceBehavior,
    ToolCallLimitBehavior,
    ToolCooldownBehavior,
    ToolSequencingBehavior,
    VerificationBehavior,
)
from harnessiq.shared.tools import ToolResult


class ToolBehaviorTests(unittest.TestCase):
    def test_tool_call_limit_behavior_hides_tools_after_limit_until_reset(self) -> None:
        layer = ToolCallLimitBehavior({"exa.*": 2})
        layer.on_agent_prepare(agent_name="demo", memory_path="memory/demo")

        visible_before = layer.filter_tool_keys(("exa.request", "serper.request"))
        self.assertEqual(visible_before, ("exa.request", "serper.request"))

        layer.on_tool_result(ToolResult(tool_key="exa.request", output={"ok": True}))
        layer.on_tool_result(ToolResult(tool_key="exa.request", output={"ok": True}))

        visible_after = layer.filter_tool_keys(("exa.request", "serper.request"))
        self.assertEqual(visible_after, ("serper.request",))
        self.assertIn("2/2 used", layer.get_parameter_sections()[-1].content)

        layer.on_post_reset()
        visible_after_reset = layer.filter_tool_keys(("exa.request", "serper.request"))
        self.assertEqual(visible_after_reset, ("exa.request", "serper.request"))

    def test_tool_sequencing_behavior_requires_prerequisite_first(self) -> None:
        layer = ToolSequencingBehavior({"artifact.write_*": ("exa.*",)})
        layer.on_agent_prepare(agent_name="demo", memory_path="memory/demo")

        visible_before = layer.filter_tool_keys(("artifact.write_json", "exa.request"))
        self.assertEqual(visible_before, ("exa.request",))

        layer.on_tool_result(ToolResult(tool_key="exa.request", output={"ok": True}))
        visible_after = layer.filter_tool_keys(("artifact.write_json", "exa.request"))
        self.assertEqual(visible_after, ("artifact.write_json", "exa.request"))
        self.assertIn("satisfied", layer.get_parameter_sections()[-1].content)

    def test_tool_cooldown_behavior_requires_intervening_tool_call(self) -> None:
        layer = ToolCooldownBehavior(("exa.*",))
        layer.on_agent_prepare(agent_name="demo", memory_path="memory/demo")

        layer.on_tool_result(ToolResult(tool_key="exa.request", output={"ok": True}))
        visible_during_cooldown = layer.filter_tool_keys(("exa.request", "serper.request"))
        self.assertEqual(visible_during_cooldown, ("serper.request",))

        layer.on_tool_result(ToolResult(tool_key="serper.request", output={"ok": True}))
        visible_after_intervening_call = layer.filter_tool_keys(("exa.request", "serper.request"))
        self.assertEqual(visible_after_intervening_call, ("exa.request", "serper.request"))
        self.assertIn("ready", layer.get_parameter_sections()[-1].content)


class PaceBehaviorTests(unittest.TestCase):
    def test_reflection_cadence_behavior_blocks_actions_until_reasoning(self) -> None:
        layer = ReflectionCadenceBehavior(
            every_n_calls=2,
            reasoning_patterns=("reason.*",),
            blocked_until_reflected=("exa.*", "artifact.*"),
        )

        layer.on_tool_result(ToolResult(tool_key="exa.request", output={"ok": True}))
        layer.on_tool_result(ToolResult(tool_key="artifact.write_json", output={"ok": True}))

        visible_pending = layer.filter_tool_keys(
            ("exa.request", "artifact.write_json", "reason.chain_of_thought")
        )
        self.assertEqual(visible_pending, ("reason.chain_of_thought",))
        self.assertIn("pending", layer.get_parameter_sections()[-1].content)

        layer.on_tool_result(ToolResult(tool_key="reason.chain_of_thought", output={"ok": True}))
        visible_after_reasoning = layer.filter_tool_keys(
            ("exa.request", "artifact.write_json", "reason.chain_of_thought")
        )
        self.assertEqual(
            visible_after_reasoning,
            ("exa.request", "artifact.write_json", "reason.chain_of_thought"),
        )

    def test_progress_checkpoint_behavior_blocks_actions_until_checkpoint(self) -> None:
        layer = ProgressCheckpointBehavior(
            every_n_calls=2,
            checkpoint_patterns=("memory.checkpoint",),
            blocked_until_checkpointed=("exa.*", "artifact.*"),
        )

        layer.on_tool_result(ToolResult(tool_key="exa.request", output={"ok": True}))
        layer.on_tool_result(ToolResult(tool_key="artifact.write_json", output={"ok": True}))

        visible_pending = layer.filter_tool_keys(
            ("exa.request", "artifact.write_json", "memory.checkpoint")
        )
        self.assertEqual(visible_pending, ("memory.checkpoint",))
        self.assertIn("pending", layer.get_parameter_sections()[-1].content)

        layer.on_tool_result(ToolResult(tool_key="memory.checkpoint", output={"ok": True}))
        visible_after_checkpoint = layer.filter_tool_keys(
            ("exa.request", "artifact.write_json", "memory.checkpoint")
        )
        self.assertEqual(
            visible_after_checkpoint,
            ("exa.request", "artifact.write_json", "memory.checkpoint"),
        )

    def test_verification_behavior_requires_validation_after_write(self) -> None:
        layer = VerificationBehavior(
            write_patterns=("artifact.write_*",),
            verification_patterns=("validation.*",),
            blocked_until_verified=("artifact.*", "control.mark_complete"),
        )

        layer.on_tool_result(ToolResult(tool_key="artifact.write_json", output={"ok": True}))

        visible_pending = layer.filter_tool_keys(
            ("artifact.write_json", "validation.schema_validate", "control.mark_complete")
        )
        self.assertEqual(visible_pending, ("validation.schema_validate",))
        self.assertIn("artifact.write_json", layer.get_parameter_sections()[-1].content)

        layer.on_tool_result(ToolResult(tool_key="validation.schema_validate", output={"ok": True}))
        visible_after_validation = layer.filter_tool_keys(
            ("artifact.write_json", "validation.schema_validate", "control.mark_complete")
        )
        self.assertEqual(
            visible_after_validation,
            ("artifact.write_json", "validation.schema_validate", "control.mark_complete"),
        )


if __name__ == "__main__":
    unittest.main()
