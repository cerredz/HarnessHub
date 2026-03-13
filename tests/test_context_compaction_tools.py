"""Tests for agent-context compaction helpers and tools."""

from __future__ import annotations

import unittest

from src.shared.tools import HEAVY_COMPACTION, LOG_COMPACTION, REMOVE_TOOL_RESULTS, REMOVE_TOOLS
from src.tools import (
    apply_log_compaction,
    create_builtin_registry,
    create_context_compaction_tools,
    heavy_compact_context,
    remove_tool_entries,
    remove_tool_result_entries,
    summarize_and_log_compact,
)
from src.tools.registry import ToolRegistry


class ContextCompactionToolsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.context_window = [
            {"kind": "parameter", "label": "identity", "content": "Agent identity"},
            {"kind": "parameter", "label": "preferences", "content": "Job preferences"},
            {"kind": "message", "role": "user", "content": "Find a new role."},
            {
                "kind": "tool_call",
                "tool_key": "browser.search_jobs",
                "tool_call_id": "call_1",
                "arguments": {"query": "python"},
            },
            {
                "kind": "tool_result",
                "tool_key": "browser.search_jobs",
                "tool_call_id": "call_1",
                "output": {"count": 2},
            },
            {"kind": "message", "role": "assistant", "content": "I found two roles."},
            {
                "kind": "tool_call",
                "tool_key": "browser.open_job",
                "tool_call_id": "call_2",
                "arguments": {"job_id": "abc"},
            },
            {
                "kind": "tool_result",
                "tool_key": "browser.open_job",
                "tool_call_id": "call_2",
                "output": {"title": "Platform Engineer"},
            },
        ]

    def test_remove_tool_result_entries_preserves_non_tool_result_order(self) -> None:
        compacted = remove_tool_result_entries(self.context_window)

        self.assertEqual([entry["kind"] for entry in compacted], ["parameter", "parameter", "message", "tool_call", "message", "tool_call"])
        self.assertEqual(self.context_window[4]["kind"], "tool_result")

    def test_remove_tool_entries_removes_calls_and_results(self) -> None:
        compacted = remove_tool_entries(self.context_window)

        self.assertEqual([entry["kind"] for entry in compacted], ["parameter", "parameter", "message", "message"])

    def test_heavy_compact_context_keeps_only_leading_parameter_prefix(self) -> None:
        compacted = heavy_compact_context(self.context_window)

        self.assertEqual(compacted, self.context_window[:2])

    def test_apply_log_compaction_appends_string_summary_after_parameters(self) -> None:
        compacted = apply_log_compaction(self.context_window, "User asked for roles and two jobs were found.")

        self.assertEqual(
            compacted,
            [
                self.context_window[0],
                self.context_window[1],
                {
                    "kind": "summary",
                    "content": "User asked for roles and two jobs were found.",
                },
            ],
        )

    def test_apply_log_compaction_accepts_prebuilt_summary_entry(self) -> None:
        summary = {"kind": "summary", "content": "Condensed run log.", "metadata": {"source": "summarizer"}}

        compacted = apply_log_compaction(self.context_window, summary)

        self.assertEqual(compacted[-1], summary)

    def test_summarize_and_log_compact_uses_full_window_copy(self) -> None:
        observed: list[list[dict[str, object]]] = []

        def summarizer(context_window: list[dict[str, object]]) -> str:
            observed.append(context_window)
            context_window[0]["content"] = "mutated"
            return "Summary from separate agent."

        compacted = summarize_and_log_compact(self.context_window, summarizer)

        self.assertEqual(observed[0][0]["content"], "mutated")
        self.assertEqual(self.context_window[0]["content"], "Agent identity")
        self.assertEqual(compacted[-1]["content"], "Summary from separate agent.")

    def test_registry_executes_remove_tool_results_tool(self) -> None:
        registry = create_builtin_registry()

        result = registry.execute(REMOVE_TOOL_RESULTS, {"context_window": self.context_window})

        self.assertEqual([entry["kind"] for entry in result.output["context_window"]], ["parameter", "parameter", "message", "tool_call", "message", "tool_call"])

    def test_registry_executes_remove_tools_tool(self) -> None:
        registry = create_builtin_registry()

        result = registry.execute(REMOVE_TOOLS, {"context_window": self.context_window})

        self.assertEqual([entry["kind"] for entry in result.output["context_window"]], ["parameter", "parameter", "message", "message"])

    def test_registry_executes_heavy_compaction_tool(self) -> None:
        registry = create_builtin_registry()

        result = registry.execute(HEAVY_COMPACTION, {"context_window": self.context_window})

        self.assertEqual(result.output["context_window"], self.context_window[:2])

    def test_registry_executes_log_compaction_tool(self) -> None:
        registry = create_builtin_registry()

        result = registry.execute(
            LOG_COMPACTION,
            {
                "context_window": self.context_window,
                "summary": "Context stripped to parameter block and a run log.",
            },
        )

        self.assertEqual(
            result.output["context_window"],
            [
                self.context_window[0],
                self.context_window[1],
                {
                    "kind": "summary",
                    "content": "Context stripped to parameter block and a run log.",
                },
            ],
        )

    def test_custom_log_compaction_tool_can_inject_a_summarizer(self) -> None:
        observed: list[list[dict[str, object]]] = []

        def summarizer(context_window: list[dict[str, object]]) -> str:
            observed.append(context_window)
            return "Injected summary."

        registry = ToolRegistry(create_context_compaction_tools(log_summarizer=summarizer))

        result = registry.execute(LOG_COMPACTION, {"context_window": self.context_window})

        self.assertEqual(len(observed), 1)
        self.assertEqual(observed[0][2]["content"], "Find a new role.")
        self.assertEqual(
            result.output["context_window"],
            [
                self.context_window[0],
                self.context_window[1],
                {
                    "kind": "summary",
                    "content": "Injected summary.",
                },
            ],
        )

    def test_invalid_context_entry_kind_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            heavy_compact_context([{"kind": "unknown", "content": "bad"}])


if __name__ == "__main__":
    unittest.main()
