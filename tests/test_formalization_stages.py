from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harnessiq.formalization.stages import (
    STAGE_COMPLETE_TOOL,
    SimpleStageSpec,
    StageAdvancementError,
    StageAwareToolExecutor,
    StageContext,
    StageLayer,
    StageSpec,
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


class _RecordingStage(StageSpec):
    def __init__(
        self,
        *,
        name: str,
        description: str,
        tool_keys: tuple[str, ...],
        required_output_keys: tuple[str, ...] = (),
        completion_hint: str = "",
        complete_when=None,
        next_stage: str | None = None,
    ) -> None:
        self._name = name
        self._description = description
        self._tool_keys = tool_keys
        self._required_output_keys = required_output_keys
        self._completion_hint = completion_hint
        self._complete_when = complete_when or (lambda outputs: True)
        self._next_stage = next_stage
        self.enter_calls: list[StageContext] = []
        self.exit_calls: list[tuple[dict[str, object], StageContext]] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def build_system_prompt_fragment(self) -> str:
        return f"Focus on {self._name}."

    def build_tools(self, memory_path: Path):
        del memory_path
        return tuple(_constant_tool(tool_key, tool_key.replace(".", "_"), tool_key) for tool_key in self._tool_keys)

    def is_complete(self, outputs: dict[str, object]) -> bool:
        return bool(self._complete_when(outputs))

    @property
    def required_output_keys(self) -> tuple[str, ...]:
        return self._required_output_keys

    def get_completion_hint(self) -> str:
        return self._completion_hint

    def get_next_stage(self, outputs: dict[str, object]) -> str | None:
        del outputs
        return self._next_stage

    def on_enter(self, context: StageContext) -> None:
        self.enter_calls.append(context)

    def on_exit(self, outputs: dict[str, object], context: StageContext) -> None:
        self.exit_calls.append((dict(outputs), context))


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

    def test_stage_complete_tool_rejects_blank_summary(self) -> None:
        with self.assertRaises(ValueError):
            STAGE_COMPLETE_TOOL.execute({"summary": "   "})


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


class StageLayerTests(unittest.TestCase):
    def test_stage_layer_rejects_invalid_stage_lists(self) -> None:
        with self.assertRaises(ValueError):
            StageLayer(())

        with self.assertRaises(ValueError):
            StageLayer((
                _RecordingStage(name="  ", description="blank", tool_keys=()),
            ))

        with self.assertRaises(ValueError):
            StageLayer((
                _RecordingStage(name="dup", description="one", tool_keys=()),
                _RecordingStage(name="dup", description="two", tool_keys=()),
            ))

    def test_stage_layer_advances_linearly_persists_outputs_and_swaps_tools(self) -> None:
        discovery = _RecordingStage(
            name="discovery",
            description="Find competitors.",
            tool_keys=("stage.discovery",),
            required_output_keys=("competitors",),
            completion_hint="At least one competitor exists.",
        )
        report = _RecordingStage(
            name="report",
            description="Write the report.",
            tool_keys=("stage.report",),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            base_executor = ToolRegistry((_constant_tool("base.read", "base_read", "base"),))
            stage_executor = StageAwareToolExecutor(base=base_executor)
            layer = StageLayer((discovery, report))
            layer._stage_executor = stage_executor

            layer.on_agent_prepare(agent_name="demo_agent", memory_path=temp_dir)

            self.assertEqual(layer.current_stage.name, "discovery")
            self.assertEqual([tool.key for tool in stage_executor.definitions()], ["stage.discovery", "base.read"])
            self.assertEqual(discovery.enter_calls[0].stage_name, "discovery")
            self.assertEqual(layer.get_formalization_tools()[0].key, "formalization.stage_complete")
            self.assertIn("DISCOVERY", layer.get_parameter_sections()[1].content)
            self.assertIn("[STAGE 1/2: DISCOVERY]", layer.augment_system_prompt("Base prompt"))

            result = STAGE_COMPLETE_TOOL.execute(
                {"summary": "done", "outputs": {"competitors": ["Acme"]}}
            )
            completed = layer.on_tool_result(result)

            self.assertEqual(completed.output["summary"], "done")
            self.assertEqual(discovery.exit_calls[0][0], {"competitors": ["Acme"]})

            layer.on_pre_reset()
            layer.on_post_reset()

            self.assertEqual(layer.current_stage.name, "report")
            self.assertEqual(layer.current_stage_index, 1)
            self.assertEqual([tool.key for tool in stage_executor.definitions()], ["stage.report", "base.read"])
            self.assertIn("discovery", layer.prior_outputs)
            self.assertEqual(report.enter_calls[0].prior_stage_outputs["discovery"]["competitors"], ["Acme"])
            self.assertIn("Prior Stage Outputs", [section.title for section in layer.get_parameter_sections()])

            outputs_path = Path(temp_dir, "stage_outputs.json")
            index_path = Path(temp_dir, "stage_index.json")
            self.assertTrue(outputs_path.exists())
            self.assertTrue(index_path.exists())
            self.assertIn('"discovery"', outputs_path.read_text(encoding="utf-8"))
            self.assertIn('"current_stage": "report"', index_path.read_text(encoding="utf-8"))

    def test_stage_layer_blocks_missing_outputs_and_incomplete_payloads(self) -> None:
        gate = _RecordingStage(
            name="gate",
            description="Validate outputs.",
            tool_keys=("stage.gate",),
            required_output_keys=("items",),
            complete_when=lambda outputs: len(outputs.get("items", [])) >= 2,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            layer = StageLayer((gate,))
            layer.on_agent_prepare(agent_name="demo_agent", memory_path=temp_dir)

            missing = layer.on_tool_result(STAGE_COMPLETE_TOOL.execute({"summary": "missing"}))
            incomplete = layer.on_tool_result(
                STAGE_COMPLETE_TOOL.execute({"summary": "partial", "outputs": {"items": ["only-one"]}})
            )

            self.assertIn("Missing required outputs", missing.output["error"])
            self.assertIn("returned False", incomplete.output["error"])
            self.assertEqual(gate.exit_calls, [])
            self.assertEqual(layer.current_stage.name, "gate")

    def test_stage_layer_supports_custom_routing_and_resume_restore(self) -> None:
        discovery = _RecordingStage(
            name="discovery",
            description="Collect facts.",
            tool_keys=("stage.discovery",),
            required_output_keys=("facts",),
            next_stage="publish",
        )
        review = _RecordingStage(
            name="review",
            description="Review findings.",
            tool_keys=("stage.review",),
        )
        publish = _RecordingStage(
            name="publish",
            description="Publish results.",
            tool_keys=("stage.publish",),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            base_executor = ToolRegistry((_constant_tool("base.read", "base_read", "base"),))
            stage_executor = StageAwareToolExecutor(base=base_executor)
            layer = StageLayer((discovery, review, publish))
            layer._stage_executor = stage_executor
            layer.on_agent_prepare(agent_name="demo_agent", memory_path=temp_dir)

            layer.on_tool_result(STAGE_COMPLETE_TOOL.execute({"summary": "done", "outputs": {"facts": ["A"]}}))
            layer.on_pre_reset()
            layer.on_post_reset()

            self.assertEqual(layer.current_stage.name, "publish")
            self.assertEqual([tool.key for tool in stage_executor.definitions()], ["stage.publish", "base.read"])

            restored = StageLayer((discovery, review, publish))
            restored._stage_executor = stage_executor
            restored.on_agent_prepare(agent_name="demo_agent", memory_path=temp_dir)

            self.assertEqual(restored.current_stage.name, "publish")
            self.assertEqual(restored.prior_outputs["discovery"]["facts"], ["A"])
            self.assertEqual([tool.key for tool in stage_executor.definitions()], ["stage.publish", "base.read"])

    def test_stage_layer_raises_for_unknown_next_stage(self) -> None:
        broken = _RecordingStage(
            name="broken",
            description="Route incorrectly.",
            tool_keys=("stage.broken",),
            required_output_keys=("items",),
            next_stage="missing_stage",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            layer = StageLayer((broken,))
            layer.on_agent_prepare(agent_name="demo_agent", memory_path=temp_dir)
            layer.on_tool_result(
                STAGE_COMPLETE_TOOL.execute({"summary": "done", "outputs": {"items": [1]}})
            )
            layer.on_pre_reset()

            with self.assertRaises(StageAdvancementError):
                layer.on_post_reset()


if __name__ == "__main__":
    unittest.main()
