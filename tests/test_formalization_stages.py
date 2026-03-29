from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harnessiq.formalization.stages import (
    STAGE_COMPLETE_TOOL,
    SimpleStageSpec,
    StageAwareToolExecutor,
    StageContext,
)
from harnessiq.shared.tools import RegisteredTool, ToolDefinition
from harnessiq.tools.registry import ToolRegistry


def _constant_tool(tool_key: str, name: str, payload: object) -> RegisteredTool:
    return RegisteredTool(
        definition=ToolDefinition(
            key=tool_key,
            name=name,
            description=f"{name} tool",
            input_schema={
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": True,
            },
        ),
        handler=lambda arguments: {"payload": payload, "arguments": dict(arguments)},
    )


class _InspectableBaseExecutor(ToolRegistry):
    pass


class StageContextTests(unittest.TestCase):
    def test_stage_context_is_frozen_and_carries_runtime_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            context = StageContext(
                agent_name="demo_agent",
                memory_path=Path(temp_dir),
                reset_count=2,
                stage_index=1,
                stage_name="enrichment",
                prior_stage_outputs={"discovery": {"urls": ["https://example.test"]}},
                metadata={"source": "unit-test"},
            )

            self.assertEqual(context.agent_name, "demo_agent")
            self.assertEqual(context.memory_path, Path(temp_dir))
            self.assertEqual(context.prior_stage_outputs["discovery"]["urls"], ["https://example.test"])
            self.assertEqual(context.metadata["source"], "unit-test")


class SimpleStageSpecTests(unittest.TestCase):
    def test_simple_stage_spec_returns_configured_behavior(self) -> None:
        read_tool = _constant_tool("artifact.read", "read", {"ok": True})
        spec = SimpleStageSpec(
            name="report",
            description="Write the final report.",
            system_prompt_fragment="Use the prior stage outputs to draft the report.",
            tools=(read_tool,),
            allowed_tool_patterns=("artifact.*",),
            required_output_keys=("report_artifact",),
            completion_hint="The final report artifact has been written.",
            next_stage_hint="Next: publish.",
            next_stage="publish",
            persist_outputs=False,
        )

        self.assertEqual(spec.name, "report")
        self.assertEqual(spec.description, "Write the final report.")
        self.assertEqual(spec.build_system_prompt_fragment(), "Use the prior stage outputs to draft the report.")
        self.assertEqual(tuple(tool.key for tool in spec.build_tools(Path("."))), ("artifact.read",))
        self.assertTrue(spec.is_complete({}))
        self.assertEqual(spec.allowed_tool_patterns, ("artifact.*",))
        self.assertEqual(spec.required_output_keys, ("report_artifact",))
        self.assertEqual(spec.get_completion_hint(), "The final report artifact has been written.")
        self.assertEqual(spec.get_next_stage_hint(), "Next: publish.")
        self.assertEqual(spec.get_next_stage({}), "publish")
        self.assertFalse(spec.persist_outputs)

    def test_stage_describe_helpers_include_required_outputs_and_filters(self) -> None:
        spec = SimpleStageSpec(
            name="discovery",
            description="Find competitors.",
            allowed_tool_patterns=("exa.*",),
            required_output_keys=("competitors",),
            completion_hint="At least one competitor exists.",
        )

        self.assertIn("competitors", spec._describe_contract())
        self.assertEqual(spec._describe_rules()[0].rule_id, "STAGE-DISCOVERY-REQUIRED-OUTPUTS")
        self.assertEqual(spec._describe_rules()[1].rule_id, "STAGE-DISCOVERY-TOOL-FILTER")


class StageCompleteToolTests(unittest.TestCase):
    def test_stage_complete_tool_normalizes_summary_and_outputs(self) -> None:
        result = STAGE_COMPLETE_TOOL.execute(
            {"summary": "  complete discovery  ", "outputs": {"competitors": ["Acme"]}}
        )

        self.assertEqual(result.tool_key, "formalization.stage_complete")
        self.assertEqual(
            result.output,
            {"summary": "complete discovery", "outputs": {"competitors": ["Acme"]}},
        )

    def test_stage_complete_tool_rejects_non_mapping_outputs(self) -> None:
        with self.assertRaises(TypeError):
            STAGE_COMPLETE_TOOL.execute({"summary": "done", "outputs": ["bad"]})


class StageAwareToolExecutorTests(unittest.TestCase):
    def test_stage_tools_shadow_base_tools_and_swap_cleanly(self) -> None:
        base_registry = _InspectableBaseExecutor(
            [
                _constant_tool("shared.echo", "base_echo", "base"),
                _constant_tool("base.only", "base_only", "base-only"),
            ]
        )
        stage_registry = [
            _constant_tool("shared.echo", "stage_echo", "stage"),
            _constant_tool("stage.only", "stage_only", "stage-only"),
        ]
        executor = StageAwareToolExecutor(base=base_registry, initial_stage_tools=stage_registry)

        definitions = executor.definitions()
        self.assertEqual([definition.key for definition in definitions], ["shared.echo", "stage.only", "base.only"])
        self.assertEqual(executor.execute("shared.echo", {}).output["payload"], "stage")
        self.assertEqual(executor.execute("base.only", {}).output["payload"], "base-only")

        executor.swap_stage_tools((_constant_tool("stage.next", "stage_next", "next"),))

        swapped_definitions = executor.definitions()
        self.assertEqual([definition.key for definition in swapped_definitions], ["stage.next", "shared.echo", "base.only"])
        self.assertEqual(executor.execute("shared.echo", {}).output["payload"], "base")
        self.assertEqual(executor.execute("stage.next", {}).output["payload"], "next")

        executor.swap_stage_tools(())
        self.assertEqual([definition.key for definition in executor.definitions()], ["shared.echo", "base.only"])

    def test_stage_executor_supports_selected_definitions_and_inspection(self) -> None:
        base_registry = _InspectableBaseExecutor(
            [
                _constant_tool("filesystem.read", "read", "base-read"),
                _constant_tool("filesystem.write", "write", "base-write"),
            ]
        )
        stage_tools = (
            _constant_tool("artifact.write", "artifact_write", "stage-write"),
        )
        executor = StageAwareToolExecutor(base=base_registry, initial_stage_tools=stage_tools)

        definitions = executor.definitions(["artifact.write", "filesystem.read"])
        inspection = executor.inspect(["artifact.write", "filesystem.read"])

        self.assertEqual([definition.key for definition in definitions], ["artifact.write", "filesystem.read"])
        self.assertEqual([item["key"] for item in inspection], ["artifact.write", "filesystem.read"])
        self.assertIs(executor.base, base_registry)


if __name__ == "__main__":
    unittest.main()
