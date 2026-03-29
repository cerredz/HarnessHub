from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from harnessiq import formalization
from harnessiq.interfaces import OutputArtifactLayer
from harnessiq.formalization.artifacts import OutputArtifactSpec
from harnessiq.formalization.artifacts.format_map import resolve_output_path
from harnessiq.shared.agents import AgentPauseSignal
from harnessiq.shared.tools import (
    ARTIFACT_WRITE_JSON,
    ARTIFACT_WRITE_MARKDOWN,
    CONTROL_MARK_COMPLETE,
    FILESYSTEM_REPLACE_TEXT_FILE,
    ToolResult,
)
from harnessiq.tools.control import create_control_tools


def _output_section(layer: OutputArtifactLayer):
    return layer.get_parameter_sections()[-1]


def _tool_keys(layer: OutputArtifactLayer) -> tuple[str, ...]:
    return tuple(tool.key for tool in layer.get_formalization_tools())


def _tool(layer: OutputArtifactLayer, key: str):
    for tool in layer.get_formalization_tools():
        if tool.key == key:
            return tool
    raise AssertionError(f"Tool {key} not found.")


def _mark_complete_result(memory_path: str, summary: str = "complete") -> ToolResult:
    tool = next(tool for tool in create_control_tools(root=memory_path) if tool.key == CONTROL_MARK_COMPLETE)
    return tool.execute({"summary": summary})


class OutputArtifactLayerTests(unittest.TestCase):
    def test_layer_rejects_invalid_artifact_lists_and_required_names(self) -> None:
        with self.assertRaises(ValueError):
            OutputArtifactLayer(())

        with self.assertRaisesRegex(ValueError, "Duplicate OutputArtifactSpec name 'dup'"):
            OutputArtifactLayer(
                (
                    OutputArtifactSpec(name="dup", description="one"),
                    OutputArtifactSpec(name="dup", description="two"),
                )
            )

        with self.assertRaisesRegex(ValueError, "at least one name"):
            OutputArtifactLayer(
                (OutputArtifactSpec(name="findings", description="Findings"),),
                completion_requirement="specific",
            )

        with self.assertRaisesRegex(ValueError, "unknown artifact names"):
            OutputArtifactLayer(
                (OutputArtifactSpec(name="findings", description="Findings"),),
                completion_requirement="specific",
                required_names=("sources",),
            )

    def test_layer_renders_output_status_and_write_guidance(self) -> None:
        layer = OutputArtifactLayer(
            (
                OutputArtifactSpec(
                    name="findings",
                    description="Structured findings.",
                    file_format="markdown",
                ),
                OutputArtifactSpec(
                    name="summary_note",
                    description="Plain text summary.",
                    file_format="text",
                    path="{memory_path}/summaries/{name}.txt",
                ),
            )
        )

        with TemporaryDirectory() as temp_dir:
            layer.on_agent_prepare(agent_name="demo", memory_path=temp_dir)
            section = _output_section(layer)

        self.assertEqual(section.title, "Output Artifacts")
        self.assertIn("findings [required]  [not yet written]", section.content)
        self.assertIn('artifact.write_markdown(name="findings", ...)', section.content)
        self.assertIn("Plain text summary.", section.content)
        self.assertIn('filesystem.replace_text_file(path="', section.content)
        self.assertIn(str(Path(temp_dir) / "summaries" / "summary_note.txt"), section.content)

    def test_layer_contributes_only_needed_write_tools(self) -> None:
        layer = OutputArtifactLayer(
            (
                OutputArtifactSpec(
                    name="findings",
                    description="Structured findings.",
                    file_format="markdown",
                ),
                OutputArtifactSpec(
                    name="summary_note",
                    description="Plain text summary.",
                    file_format="text",
                ),
                OutputArtifactSpec(
                    name="external_json",
                    description="Provided elsewhere.",
                    file_format="json",
                    contributes_write_tool=False,
                ),
            )
        )

        with TemporaryDirectory() as temp_dir:
            layer.on_agent_prepare(agent_name="demo", memory_path=temp_dir)
            tool_keys = _tool_keys(layer)

        self.assertEqual(tool_keys, (ARTIFACT_WRITE_MARKDOWN, FILESYSTEM_REPLACE_TEXT_FILE))

    def test_managed_artifact_writes_mark_outputs_written(self) -> None:
        layer = OutputArtifactLayer(
            (
                OutputArtifactSpec(
                    name="findings",
                    description="Structured findings.",
                    file_format="markdown",
                ),
            )
        )

        with TemporaryDirectory() as temp_dir:
            layer.on_agent_prepare(agent_name="demo", memory_path=temp_dir)
            result = layer.on_tool_result(
                ToolResult(
                    tool_key=ARTIFACT_WRITE_MARKDOWN,
                    output={"name": "findings", "path": str(Path(temp_dir) / "artifacts" / "findings.md")},
                )
            )
            section = _output_section(layer)

        self.assertEqual(result.tool_key, ARTIFACT_WRITE_MARKDOWN)
        self.assertIn("findings [required]  [written]", section.content)

    def test_text_file_writes_mark_outputs_written_by_resolved_path(self) -> None:
        spec = OutputArtifactSpec(
            name="summary_note",
            description="Plain text summary.",
            file_format="text",
            path="{memory_path}/summaries/{name}.txt",
        )
        layer = OutputArtifactLayer((spec,))

        with TemporaryDirectory() as temp_dir:
            layer.on_agent_prepare(agent_name="demo", memory_path=temp_dir)
            text_tool = _tool(layer, FILESYSTEM_REPLACE_TEXT_FILE)
            result = text_tool.execute(
                {
                    "path": str(resolve_output_path(spec, Path(temp_dir))),
                    "content": "hello world",
                }
            )
            layer.on_tool_result(result)
            section = _output_section(layer)

        self.assertIn("summary_note [required]  [written]", section.content)

    def test_mark_complete_is_blocked_until_required_outputs_exist(self) -> None:
        layer = OutputArtifactLayer(
            (
                OutputArtifactSpec(name="findings", description="Structured findings.", file_format="markdown"),
                OutputArtifactSpec(name="sources", description="Source list.", file_format="json"),
            )
        )

        with TemporaryDirectory() as temp_dir:
            layer.on_agent_prepare(agent_name="demo", memory_path=temp_dir)
            result = layer.on_tool_result(_mark_complete_result(temp_dir))

        self.assertEqual(result.tool_key, CONTROL_MARK_COMPLETE)
        self.assertEqual(result.output["required"], ["findings", "sources"])
        self.assertEqual(result.output["written"], [])
        self.assertEqual(result.output["missing"], ["findings", "sources"])
        self.assertIn("Completion blocked.", result.output["error"])
        self.assertFalse(layer.completion_pending)
        self.assertFalse(layer.run_completed)

    def test_mark_complete_succeeds_after_required_outputs_are_written(self) -> None:
        specs = (
            OutputArtifactSpec(name="findings", description="Structured findings.", file_format="markdown"),
            OutputArtifactSpec(name="sources", description="Source list.", file_format="json"),
            OutputArtifactSpec(name="summary_note", description="Plain text summary.", file_format="text"),
        )
        layer = OutputArtifactLayer(
            specs,
            completion_requirement="specific",
            required_names=("findings", "sources"),
        )

        with TemporaryDirectory() as temp_dir:
            layer.on_agent_prepare(agent_name="demo", memory_path=temp_dir)
            markdown_tool = _tool(layer, ARTIFACT_WRITE_MARKDOWN)
            json_tool = _tool(layer, ARTIFACT_WRITE_JSON)
            findings_result = markdown_tool.execute({"name": "findings", "content": "Findings body"})
            sources_result = json_tool.execute({"name": "sources", "data": [{"url": "https://example.test"}]})
            layer.on_tool_result(findings_result)
            layer.on_tool_result(sources_result)

            completion_result = _mark_complete_result(temp_dir, summary="done")
            final_result = layer.on_tool_result(completion_result)
            before_reset_section = _output_section(layer)
            layer.on_post_reset()

        self.assertIsInstance(final_result.output, AgentPauseSignal)
        self.assertTrue(layer.run_completed)
        self.assertFalse(layer.completion_pending)
        self.assertIn("findings [required]  [written]", before_reset_section.content)
        self.assertIn("sources [required]  [written]", before_reset_section.content)
        self.assertIn("summary_note  [not yet written]", before_reset_section.content)

    def test_runtime_and_interface_exports_include_output_artifact_layer(self) -> None:
        self.assertIs(formalization.OutputArtifactLayer, OutputArtifactLayer)


if __name__ == "__main__":
    unittest.main()
