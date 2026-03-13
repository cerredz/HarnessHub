"""Tests for the general-purpose tool family."""

from __future__ import annotations

import unittest

from src.agents import AgentPauseSignal
from src.shared.tools import CONTROL_PAUSE_FOR_HUMAN, RECORDS_FILTER_RECORDS, TEXT_NORMALIZE_WHITESPACE
from src.tools import (
    count_by_field,
    create_builtin_registry,
    filter_records,
    limit_records,
    normalize_whitespace,
    pause_for_human,
    regex_extract,
    select_fields,
    sort_records,
    truncate_text,
    unique_records,
)


class GeneralPurposeToolsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.records = [
            {"id": 1, "status": "open", "priority": 2, "tags": ["backend", "urgent"]},
            {"id": 2, "status": "closed", "priority": 1, "tags": ["frontend"]},
            {"id": 3, "status": "open", "priority": 3, "tags": ["backend"]},
            {"id": 4, "status": "draft", "tags": []},
        ]

    def test_normalize_whitespace_optionally_preserves_newlines(self) -> None:
        collapsed = normalize_whitespace("  hello   world  ")
        preserved = normalize_whitespace(" line  one\n  line   two ", preserve_newlines=True)

        self.assertEqual(collapsed, "hello world")
        self.assertEqual(preserved, "line one\nline two")

    def test_regex_extract_returns_match_metadata(self) -> None:
        matches = regex_extract(
            "Alpha alpha BETA",
            r"(?P<word>alpha)",
            ignore_case=True,
        )

        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0]["match"], "Alpha")
        self.assertEqual(matches[0]["named_groups"], {"word": "Alpha"})

    def test_truncate_text_supports_middle_truncation(self) -> None:
        truncated = truncate_text("abcdefghij", 7, position="middle")

        self.assertEqual(truncated, "ab...ij")

    def test_regex_extract_raises_clear_error_for_invalid_pattern(self) -> None:
        with self.assertRaisesRegex(ValueError, "Invalid regex pattern"):
            regex_extract("text", "(")

    def test_select_fields_can_include_missing_fields(self) -> None:
        projected = select_fields(self.records, ["id", "priority"], include_missing=True)

        self.assertEqual(projected[0], {"id": 1, "priority": 2})
        self.assertEqual(projected[-1], {"id": 4, "priority": None})

    def test_filter_records_supports_case_insensitive_contains(self) -> None:
        filtered = filter_records(
            self.records,
            field="status",
            operator="contains",
            value="OPEN",
            case_insensitive=True,
        )

        self.assertEqual([record["id"] for record in filtered], [1, 3])

    def test_sort_records_keeps_missing_values_last_by_default(self) -> None:
        sorted_records = sort_records(self.records, field="priority", descending=True)

        self.assertEqual([record["id"] for record in sorted_records], [3, 1, 2, 4])

    def test_limit_records_applies_offset(self) -> None:
        limited = limit_records(self.records, limit=2, offset=1)

        self.assertEqual([record["id"] for record in limited], [2, 3])

    def test_unique_records_deduplicates_by_field(self) -> None:
        records = [
            {"id": 1, "status": "open"},
            {"id": 2, "status": "open"},
            {"id": 3, "status": "closed"},
        ]

        unique = unique_records(records, field="status")

        self.assertEqual(unique, [{"id": 1, "status": "open"}, {"id": 3, "status": "closed"}])

    def test_count_by_field_preserves_first_seen_order(self) -> None:
        counts = count_by_field(self.records, field="status")

        self.assertEqual(
            counts,
            [
                {"value": "open", "count": 2},
                {"value": "closed", "count": 1},
                {"value": "draft", "count": 1},
            ],
        )

    def test_pause_for_human_returns_agent_pause_signal(self) -> None:
        signal = pause_for_human("approval required", details={"step": "send email"})

        self.assertIsInstance(signal, AgentPauseSignal)
        self.assertEqual(signal.reason, "approval required")
        self.assertEqual(signal.details, {"step": "send email"})

    def test_registry_executes_general_purpose_builtins(self) -> None:
        registry = create_builtin_registry()

        normalized = registry.execute(TEXT_NORMALIZE_WHITESPACE, {"text": "  spaced   out  "})
        filtered = registry.execute(
            RECORDS_FILTER_RECORDS,
            {
                "records": self.records,
                "field": "status",
                "operator": "eq",
                "value": "open",
            },
        )
        pause_signal = registry.execute(CONTROL_PAUSE_FOR_HUMAN, {"reason": "needs review"})

        self.assertEqual(normalized.output, {"text": "spaced out"})
        self.assertEqual([record["id"] for record in filtered.output["records"]], [1, 3])
        self.assertIsInstance(pause_signal.output, AgentPauseSignal)
        self.assertEqual(pause_signal.output.reason, "needs review")

    def test_invalid_filter_operator_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            filter_records(self.records, field="status", operator="between", value="open")


if __name__ == "__main__":
    unittest.main()

