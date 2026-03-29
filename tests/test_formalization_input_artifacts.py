from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from harnessiq import formalization
from harnessiq.interfaces import InputArtifactLayer
from harnessiq.formalization.artifacts import (
    ArtifactNotFoundError,
    InjectionPolicy,
    InputArtifactSpec,
)


def _artifact_sections(layer: InputArtifactLayer) -> list[object]:
    return list(layer.get_parameter_sections()[1:])


class InputArtifactLayerTests(unittest.TestCase):
    def test_required_missing_input_raises_on_prepare(self) -> None:
        layer = InputArtifactLayer(
            (
                InputArtifactSpec(
                    name="client_brief",
                    path="inputs/brief.md",
                    description="Required brief.",
                    file_format="markdown",
                ),
            )
        )

        with TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ArtifactNotFoundError, "client_brief"):
                layer.on_agent_prepare(agent_name="demo", memory_path=temp_dir)

    def test_optional_missing_input_renders_placeholder_section(self) -> None:
        layer = InputArtifactLayer(
            (
                InputArtifactSpec(
                    name="prior_findings",
                    path="findings.md",
                    description="Prior findings, if they exist.",
                    file_format="markdown",
                    required=False,
                ),
            )
        )

        with TemporaryDirectory() as temp_dir:
            layer.on_agent_prepare(agent_name="demo", memory_path=temp_dir)
            sections = _artifact_sections(layer)

        self.assertEqual(sections[0].title, "Input: prior_findings")
        self.assertIn("[File not yet available:", sections[0].content)
        self.assertIn("Prior findings, if they exist.", sections[0].content)

    def test_refresh_on_reset_false_uses_cached_content(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "brief.md"
            source.write_text("version one", encoding="utf-8")
            layer = InputArtifactLayer(
                (
                    InputArtifactSpec(
                        name="client_brief",
                        path="brief.md",
                        description="Client brief.",
                        injection_policy=InjectionPolicy(refresh_on_reset=False),
                    ),
                )
            )

            layer.on_agent_prepare(agent_name="demo", memory_path=temp_dir)
            first = _artifact_sections(layer)[0]
            source.write_text("version two", encoding="utf-8")
            layer.on_post_reset()
            second = _artifact_sections(layer)[0]

        self.assertIn("version one", first.content)
        self.assertIn("version one", second.content)
        self.assertNotIn("version two", second.content)

    def test_refresh_on_reset_true_rereads_after_reset(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "brief.md"
            source.write_text("version one", encoding="utf-8")
            layer = InputArtifactLayer(
                (
                    InputArtifactSpec(
                        name="client_brief",
                        path="brief.md",
                        description="Client brief.",
                        injection_policy=InjectionPolicy(refresh_on_reset=True),
                    ),
                )
            )

            layer.on_agent_prepare(agent_name="demo", memory_path=temp_dir)
            first = _artifact_sections(layer)[0]
            source.write_text("version two", encoding="utf-8")
            layer.on_post_reset()
            second = _artifact_sections(layer)[0]

        self.assertIn("version one", first.content)
        self.assertIn("version two", second.content)

    def test_refresh_on_reset_false_keeps_optional_missing_file_cached(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "optional.md"
            layer = InputArtifactLayer(
                (
                    InputArtifactSpec(
                        name="optional_notes",
                        path="optional.md",
                        description="Optional notes.",
                        required=False,
                        injection_policy=InjectionPolicy(refresh_on_reset=False),
                    ),
                )
            )

            layer.on_agent_prepare(agent_name="demo", memory_path=temp_dir)
            initial = _artifact_sections(layer)[0]
            source.write_text("appeared later", encoding="utf-8")
            layer.on_post_reset()
            later = _artifact_sections(layer)[0]

        self.assertIn("[File not yet available:", initial.content)
        self.assertIn("[File not yet available:", later.content)
        self.assertNotIn("appeared later", later.content)

    def test_oversize_handling_supports_truncate_skip_and_header_only(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            oversized = "0123456789ABCDEFGHIJ"
            (root / "truncate.txt").write_text(oversized, encoding="utf-8")
            (root / "skip.txt").write_text(oversized, encoding="utf-8")
            (root / "header.txt").write_text(oversized, encoding="utf-8")

            truncate_layer = InputArtifactLayer(
                (
                    InputArtifactSpec(
                        name="truncate_case",
                        path="truncate.txt",
                        description="Truncate oversized content.",
                        injection_policy=InjectionPolicy(max_chars=10, on_oversize="truncate"),
                    ),
                )
            )
            skip_layer = InputArtifactLayer(
                (
                    InputArtifactSpec(
                        name="skip_case",
                        path="skip.txt",
                        description="Skip oversized content.",
                        injection_policy=InjectionPolicy(max_chars=10, on_oversize="skip"),
                    ),
                )
            )
            header_only_layer = InputArtifactLayer(
                (
                    InputArtifactSpec(
                        name="header_only_case",
                        path="header.txt",
                        description="Header-only oversized content.",
                        injection_policy=InjectionPolicy(max_chars=10, on_oversize="header_only"),
                    ),
                )
            )

            for layer in (truncate_layer, skip_layer, header_only_layer):
                layer.on_agent_prepare(agent_name="demo", memory_path=temp_dir)

            truncate_section = _artifact_sections(truncate_layer)[0]
            skip_sections = _artifact_sections(skip_layer)
            header_only_section = _artifact_sections(header_only_layer)[0]

        self.assertIn("[TRUNCATED:", truncate_section.content)
        self.assertEqual(skip_sections, [])
        self.assertIn("[Content omitted:", header_only_section.content)
        self.assertNotIn(oversized, header_only_section.content)

    def test_custom_filter_can_suppress_initial_reset_and_allow_later_resets(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "reference.json"
            source.write_text('{"items":[1,2,3]}', encoding="utf-8")
            layer = InputArtifactLayer(
                (
                    InputArtifactSpec(
                        name="reference_data",
                        path="reference.json",
                        description="Reference data.",
                        file_format="json",
                        injection_policy=InjectionPolicy(
                            custom_filter=lambda content, reset_count: reset_count > 0 and len(content) > 10,
                        ),
                    ),
                )
            )

            layer.on_agent_prepare(agent_name="demo", memory_path=temp_dir)
            initial_sections = _artifact_sections(layer)
            layer.on_post_reset()
            later_sections = _artifact_sections(layer)

        self.assertEqual(initial_sections, [])
        self.assertEqual(later_sections[0].title, "Input: reference_data")
        self.assertIn('"items": [', later_sections[0].content)

    def test_json_and_csv_inputs_are_rendered_with_format_specific_transforms(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "reference.json").write_text('{"b":2,"a":1}', encoding="utf-8")
            (root / "table.csv").write_text("name,value\nalpha,1\nbeta,2\n", encoding="utf-8")
            layer = InputArtifactLayer(
                (
                    InputArtifactSpec(
                        name="reference_data",
                        path="reference.json",
                        description="Reference JSON.",
                        file_format="json",
                    ),
                    InputArtifactSpec(
                        name="table_data",
                        path="table.csv",
                        description="Tabular data.",
                        file_format="csv",
                    ),
                )
            )

            layer.on_agent_prepare(agent_name="demo", memory_path=temp_dir)
            sections = _artifact_sections(layer)

        self.assertIn('"a": 1', sections[0].content)
        self.assertIn("[HEADER] name,value", sections[1].content)

    def test_runtime_and_interface_exports_include_input_artifact_layer(self) -> None:
        self.assertIs(formalization.InputArtifactLayer, InputArtifactLayer)


if __name__ == "__main__":
    unittest.main()
