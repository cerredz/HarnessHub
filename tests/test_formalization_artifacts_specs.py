from __future__ import annotations

import unittest
from pathlib import Path

from harnessiq import formalization
from harnessiq.interfaces import formalization as interface_formalization
from harnessiq.interfaces import (
    CompletionRequirement,
    InjectionPolicy,
    InputArtifactSpec,
    OutputArtifactSpec,
    resolve_artifact_path,
    resolve_output_path,
    resolve_write_tool_key,
)
from harnessiq.formalization.artifacts import (
    ArtifactNotFoundError,
    FORMAT_EXTENSION_MAP,
    FORMAT_TOOL_MAP,
    OutputArtifactMissingError,
    validate_input_artifact_specs,
    validate_output_artifact_specs,
)
from harnessiq.shared.tools import (
    ARTIFACT_APPEND_RUN_LOG,
    ARTIFACT_WRITE_JSON,
    ARTIFACT_WRITE_MARKDOWN,
    FILESYSTEM_REPLACE_TEXT_FILE,
)


class InjectionPolicyTests(unittest.TestCase):
    def test_injection_policy_rejects_negative_max_chars(self) -> None:
        with self.assertRaisesRegex(ValueError, "max_chars"):
            InjectionPolicy(max_chars=-1)

    def test_injection_policy_rejects_blank_section_title_template(self) -> None:
        with self.assertRaisesRegex(ValueError, "section_title_template"):
            InjectionPolicy(section_title_template="   ")


class InputArtifactSpecTests(unittest.TestCase):
    def test_input_artifact_spec_uses_expected_defaults(self) -> None:
        spec = InputArtifactSpec(
            name="client_brief",
            path="inputs/brief.md",
            description="The source brief for this run.",
            file_format="markdown",
        )

        self.assertEqual(spec.file_format, "markdown")
        self.assertTrue(spec.required)
        self.assertEqual(spec.injection_policy.max_chars, 100_000)

    def test_input_artifact_spec_rejects_invalid_name_and_format(self) -> None:
        with self.assertRaisesRegex(ValueError, "snake_case"):
            InputArtifactSpec(
                name="ClientBrief",
                path="inputs/brief.md",
                description="The source brief.",
            )

        with self.assertRaisesRegex(ValueError, "unsupported format"):
            InputArtifactSpec(
                name="client_brief",
                path="inputs/brief.md",
                description="The source brief.",
                file_format="xml",  # type: ignore[arg-type]
            )

    def test_validate_input_artifact_specs_rejects_duplicate_names(self) -> None:
        specs = (
            InputArtifactSpec(
                name="client_brief",
                path="inputs/brief.md",
                description="First brief.",
            ),
            InputArtifactSpec(
                name="client_brief",
                path="inputs/brief-2.md",
                description="Duplicate brief name.",
            ),
        )

        with self.assertRaisesRegex(ValueError, "Duplicate InputArtifactSpec name"):
            validate_input_artifact_specs(specs)


class OutputArtifactSpecTests(unittest.TestCase):
    def test_output_artifact_spec_uses_expected_defaults(self) -> None:
        spec = OutputArtifactSpec(
            name="executive_memo",
            description="The final memo output.",
        )

        self.assertEqual(spec.file_format, "markdown")
        self.assertIsNone(spec.path)
        self.assertIsNone(spec.write_tool_key)
        self.assertTrue(spec.contributes_write_tool)

    def test_output_artifact_spec_rejects_invalid_name_and_format(self) -> None:
        with self.assertRaisesRegex(ValueError, "snake_case"):
            OutputArtifactSpec(
                name="ExecutiveMemo",
                description="The final memo output.",
            )

        with self.assertRaisesRegex(ValueError, "unsupported format"):
            OutputArtifactSpec(
                name="executive_memo",
                description="The final memo output.",
                file_format="yaml",  # type: ignore[arg-type]
            )

    def test_validate_output_artifact_specs_rejects_duplicate_names(self) -> None:
        specs = (
            OutputArtifactSpec(
                name="executive_memo",
                description="First memo.",
            ),
            OutputArtifactSpec(
                name="executive_memo",
                description="Duplicate memo name.",
            ),
        )

        with self.assertRaisesRegex(ValueError, "Duplicate OutputArtifactSpec name"):
            validate_output_artifact_specs(specs)


class ArtifactFormatMapTests(unittest.TestCase):
    def test_format_maps_include_expected_runtime_tool_keys(self) -> None:
        self.assertEqual(FORMAT_TOOL_MAP["markdown"], ARTIFACT_WRITE_MARKDOWN)
        self.assertEqual(FORMAT_TOOL_MAP["json"], ARTIFACT_WRITE_JSON)
        self.assertEqual(FORMAT_TOOL_MAP["jsonl"], ARTIFACT_APPEND_RUN_LOG)
        self.assertEqual(FORMAT_TOOL_MAP["text"], FILESYSTEM_REPLACE_TEXT_FILE)
        self.assertEqual(FORMAT_EXTENSION_MAP["text"], ".txt")

    def test_resolve_artifact_path_renders_templates_and_relative_paths(self) -> None:
        memory_path = Path("memory/demo-agent")

        rendered = resolve_artifact_path(
            "{memory_path}/inputs/{name}.md",
            memory_path=memory_path,
            name="client_brief",
        )
        relative = resolve_artifact_path(
            "inputs/{name}.json",
            memory_path=memory_path,
            name="reference_data",
        )

        self.assertEqual(rendered, Path("memory/demo-agent/inputs/client_brief.md"))
        self.assertEqual(relative, Path("memory/demo-agent/inputs/reference_data.json"))

    def test_resolve_write_tool_key_and_output_path_follow_format_defaults(self) -> None:
        memory_path = Path("memory/demo-agent")
        markdown_spec = OutputArtifactSpec(
            name="executive_memo",
            description="Final memo.",
            file_format="markdown",
        )
        text_spec = OutputArtifactSpec(
            name="summary_note",
            description="Plain-text summary.",
            file_format="text",
        )
        overridden = OutputArtifactSpec(
            name="sources",
            description="Structured sources.",
            file_format="json",
            path="{memory_path}/exports/{name}.json",
            write_tool_key="custom.write_json",
        )

        self.assertEqual(resolve_write_tool_key(markdown_spec), ARTIFACT_WRITE_MARKDOWN)
        self.assertEqual(
            resolve_output_path(markdown_spec, memory_path),
            Path("memory/demo-agent/artifacts/executive_memo.md"),
        )
        self.assertEqual(resolve_write_tool_key(text_spec), FILESYSTEM_REPLACE_TEXT_FILE)
        self.assertEqual(
            resolve_output_path(text_spec, memory_path),
            Path("memory/demo-agent/outputs/summary_note.txt"),
        )
        self.assertEqual(resolve_write_tool_key(overridden), "custom.write_json")
        self.assertEqual(
            resolve_output_path(overridden, memory_path),
            Path("memory/demo-agent/exports/sources.json"),
        )


class ArtifactExportsTests(unittest.TestCase):
    def test_runtime_and_interface_exports_expose_artifact_spec_surface(self) -> None:
        self.assertIs(formalization.InputArtifactSpec, InputArtifactSpec)
        self.assertIs(formalization.OutputArtifactSpec, OutputArtifactSpec)
        self.assertIs(interface_formalization.InputArtifactSpec, InputArtifactSpec)
        self.assertIs(interface_formalization.OutputArtifactSpec, OutputArtifactSpec)
        self.assertEqual(CompletionRequirement.__args__, ("all", "specific", "none"))

    def test_artifact_exceptions_have_specific_types(self) -> None:
        self.assertTrue(issubclass(ArtifactNotFoundError, FileNotFoundError))
        self.assertTrue(issubclass(OutputArtifactMissingError, RuntimeError))


if __name__ == "__main__":
    unittest.main()
