"""Focused coverage for the net-new builtin tool families."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from harnessiq.shared.agents import AgentPauseSignal
from harnessiq.tools.artifact import create_artifact_tools
from harnessiq.tools.control import create_control_tools
from harnessiq.tools.filesystem_safe import create_filesystem_safe_tools
from harnessiq.tools.memory import create_memory_tools
from harnessiq.tools.records import flatten_records, join_records, unique_records
from harnessiq.tools.text import create_text_tools, extract_code_blocks, normalize_text, template_fill
from harnessiq.tools.validation import gate, require_fields, schema_validate


class TextCatalogToolsTests(unittest.TestCase):
    def test_normalize_text_rewrites_smart_quotes_and_control_chars(self) -> None:
        value = normalize_text("\u201cHello\u201d\x00", normalize_quotes=True)

        self.assertEqual(value, '"Hello"')

    def test_registry_executes_template_fill_and_reports_missing_placeholders(self) -> None:
        registry = {tool.key: tool for tool in create_text_tools()}

        result = registry["text.template_fill"].handler(
            {
                "template": "Hello {{name}} from {{team}}",
                "values": {"name": "Ada"},
            }
        )

        self.assertEqual(result["text"], "Hello Ada from {{team}}")
        self.assertEqual(result["filled_placeholders"], ["name"])
        self.assertEqual(result["missing_placeholders"], ["team"])

    def test_extract_code_blocks_filters_by_language(self) -> None:
        blocks = extract_code_blocks(
            "```python\nprint(1)\n```\n```json\n{}\n```",
            language_filter=["python"],
            include_offsets=True,
        )

        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["language"], "python")
        self.assertIn("start_offset", blocks[0])

    def test_template_fill_strict_mode_rejects_missing_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "Missing template values"):
            template_fill("Hello {{name}} {{team}}", {"name": "Ada"}, strict=True)


class RecordsCatalogToolsTests(unittest.TestCase):
    def test_unique_records_can_keep_longest_field(self) -> None:
        unique, dropped = unique_records(
            [
                {"id": 1, "email": "a@example.com", "name": "Ada"},
                {"id": 2, "email": "a@example.com", "name": "Ada Lovelace"},
                {"id": 3, "email": "b@example.com", "name": "Grace"},
            ],
            ["email"],
            keep="longest_field",
            longest_field="name",
        )

        self.assertEqual([record["id"] for record in unique], [2, 3])
        self.assertEqual([record["id"] for record in dropped], [1])

    def test_join_records_prefixes_conflicting_right_fields(self) -> None:
        records = join_records(
            [{"id": 1, "status": "open"}],
            [{"id": 1, "status": "remote", "owner": "ops"}],
            "id",
            join_type="inner",
        )

        self.assertEqual(
            records,
            [{"id": 1, "status": "open", "right_status": "remote", "owner": "ops"}],
        )

    def test_flatten_records_can_limit_fields_and_expand_lists(self) -> None:
        records = flatten_records(
            [{"profile": {"city": "New York"}, "tags": ["a", "b"], "name": "Ada"}],
            fields=["profile", "tags"],
            expand_lists=True,
        )

        self.assertEqual(
            records,
            [{"profile.city": "New York", "tags.0": "a", "tags.1": "b", "name": "Ada"}],
        )


class FilesystemSafeToolsTests(unittest.TestCase):
    def test_exists_handles_no_follow_symlinks_for_regular_files(self) -> None:
        with TemporaryDirectory() as tmp:
            target = Path(tmp) / "example.txt"
            target.write_text("hello", encoding="utf-8")
            registry = {tool.key: tool for tool in create_filesystem_safe_tools()}

            result = registry["filesystem_safe.exists"].handler(
                {"path": str(target), "follow_symlinks": False, "expect_type": "file"}
            )

            self.assertTrue(result["exists"])
            self.assertEqual(result["entry_type"], "file")
            self.assertTrue(result["expected_type_matches"])

    def test_write_append_and_diff_tools_round_trip_text(self) -> None:
        with TemporaryDirectory() as tmp:
            registry = {tool.key: tool for tool in create_filesystem_safe_tools()}
            target = Path(tmp) / "notes.txt"

            registry["filesystem_safe.write"].handler({"path": str(target), "content": "alpha"})
            registry["filesystem_safe.append"].handler({"path": str(target), "content": "beta"})
            diff = registry["filesystem_safe.diff"].handler(
                {
                    "left": "alpha",
                    "right": target.read_text(encoding="utf-8"),
                    "input_mode": "strings",
                    "format": "summary",
                }
            )

            self.assertIn("beta", target.read_text(encoding="utf-8"))
            self.assertGreater(diff["lines_added"] + diff["lines_changed"], 0)


class StatefulCatalogToolsTests(unittest.TestCase):
    def test_memory_load_missing_key_reports_not_found(self) -> None:
        with TemporaryDirectory() as tmp:
            registry = {tool.key: tool for tool in create_memory_tools(root=tmp)}

            result = registry["memory.load"].handler({"key": "missing"})

            self.assertFalse(result["found"])
            self.assertIsNone(result["value"])

    def test_memory_checkpoint_and_compare_capture_changed_fields(self) -> None:
        with TemporaryDirectory() as tmp:
            registry = {tool.key: tool for tool in create_memory_tools(root=tmp)}

            first = registry["memory.checkpoint"].handler(
                {"fields": {"status": {"phase": 1}, "count": 1}, "checkpoint_label": "phase"}
            )
            second = registry["memory.checkpoint"].handler(
                {"fields": {"status": {"phase": 2}, "count": 1}, "checkpoint_label": "phase"}
            )
            diff = registry["memory.compare_checkpoints"].handler(
                {"checkpoint_a": first["checkpoint_id"], "checkpoint_b": second["checkpoint_id"]}
            )

            self.assertEqual(diff["added_fields"], [])
            self.assertEqual(diff["removed_fields"], [])
            self.assertEqual(diff["changed_fields"], [{"field": "status", "old": {"phase": 1}, "new": {"phase": 2}}])

    def test_control_mark_complete_returns_completion_pause_signal(self) -> None:
        with TemporaryDirectory() as tmp:
            registry = {tool.key: tool for tool in create_control_tools(root=tmp)}

            signal = registry["control.mark_complete"].handler({"summary": "done"})

            self.assertIsInstance(signal, AgentPauseSignal)
            self.assertEqual(signal.details["status"], "completed")

    def test_artifact_tools_write_and_read_json_artifacts(self) -> None:
        with TemporaryDirectory() as tmp:
            registry = {tool.key: tool for tool in create_artifact_tools(root=tmp)}

            registry["artifact.write_json"].handler({"name": "state", "data": {"count": 2}})
            listing = registry["artifact.list_artifacts"].handler({})
            loaded = registry["artifact.read_artifact"].handler({"name": "state", "parse_json": True})

            self.assertEqual(listing["count"], 1)
            self.assertTrue(loaded["found"])
            self.assertEqual(loaded["content"], {"count": 2})


class ValidationCatalogToolsTests(unittest.TestCase):
    def test_require_fields_treats_empty_collections_as_missing(self) -> None:
        result = require_fields({"profile": {"name": []}}, ["profile.name"], nested_paths=True)

        self.assertFalse(result["valid"])
        self.assertEqual(result["missing_fields"], ["profile.name"])

    def test_schema_validate_can_coerce_string_scalars(self) -> None:
        result = schema_validate(
            {"count": "3", "enabled": "true"},
            {
                "type": "object",
                "properties": {
                    "count": {"type": "integer"},
                    "enabled": {"type": "boolean"},
                },
                "required": ["count", "enabled"],
            },
            coerce_types=True,
        )

        self.assertTrue(result["valid"])

    def test_gate_supports_required_plus_threshold_mode(self) -> None:
        result = gate(
            [
                {"check_name": "required", "valid": True},
                {"check_name": "optional-a", "valid": True},
                {"check_name": "optional-b", "valid": False},
            ],
            mode="required_plus_threshold",
            pass_fraction=2 / 3,
            required_checks=["required"],
            gate_name="phase_gate",
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["check_name"], "phase_gate")


if __name__ == "__main__":
    unittest.main()
