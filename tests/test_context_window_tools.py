"""Focused tests for the context-window manipulation tool family."""

from __future__ import annotations

import json
import unittest
from copy import deepcopy

from harnessiq.shared.agents import AgentContextRuntimeState
from harnessiq.shared.tools import (
    CONTEXT_INJECT_ASSISTANT_NOTE,
    CONTEXT_PARAM_INJECT_SECTION,
    CONTEXT_SELECT_CHECKPOINT,
    CONTEXT_SELECT_PROMOTE_AND_STRIP,
    CONTEXT_STRUCT_TRUNCATE,
    CONTEXT_SUMMARIZE_HEADLINE,
)
from harnessiq.tools.context import create_context_tools
from harnessiq.tools.registry import ToolRegistry


class _RuntimeHarness:
    def __init__(self) -> None:
        self.state = AgentContextRuntimeState()
        self.state.memory_field_rules.setdefault("continuation_pointer", "overwrite")
        self.base_sections = [
            {"kind": "parameter", "label": "Identity", "content": "Agent identity"},
        ]
        self.transcript = [
            {"kind": "assistant", "content": "Investigating the task."},
            {
                "kind": "tool_call",
                "tool_key": "browser.search_jobs",
                "arguments": {"query": "python"},
            },
            {
                "kind": "tool_result",
                "tool_key": "browser.search_jobs",
                "output": {"count": 2},
            },
            {"kind": "assistant", "content": "Two roles were found."},
        ]
        self.save_calls = 0
        self.refresh_calls = 0
        self.subcalls: list[tuple[str, str, str | None]] = []

    def get_context_window(self):
        return self.build_context_window()

    def build_context_window(self):
        sections = [deepcopy(entry) for entry in self.base_sections]
        for section in self.state.injected_sections:
            sections.append({"kind": "parameter", "label": section.label, "content": section.content})
        if self.state.memory_fields or self.state.directives or self.state.checkpoints:
            payload = {
                "checkpoints": sorted(self.state.checkpoints),
                "directives": [directive.directive for directive in self.state.directives],
                "memory_fields": deepcopy(self.state.memory_fields),
            }
            sections.append(
                {
                    "kind": "parameter",
                    "label": "Context Memory",
                    "content": json.dumps(payload, sort_keys=True, default=str),
                }
            )
        return [*sections, *deepcopy(self.transcript)]

    def save_runtime_state(self) -> None:
        self.save_calls += 1

    def refresh_parameters(self) -> None:
        self.refresh_calls += 1

    def run_model_subcall(self, *, system_prompt: str, transcript_text: str, model_override: str | None = None) -> str:
        self.subcalls.append((system_prompt, transcript_text, model_override))
        return "summarized transcript"


class ContextWindowToolsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = _RuntimeHarness()
        self.registry = ToolRegistry(
            create_context_tools(
                get_context_window=self.runtime.get_context_window,
                get_runtime_state=lambda: self.runtime.state,
                save_runtime_state=self.runtime.save_runtime_state,
                refresh_parameters=self.runtime.refresh_parameters,
                get_reset_count=lambda: 2,
                get_cycle_index=lambda: 7,
                get_system_prompt=lambda: "Investigate job listings thoroughly.",
                run_model_subcall=self.runtime.run_model_subcall,
            )
        )

    def test_headline_summary_preserves_parameters_and_replaces_transcript(self) -> None:
        result = self.registry.execute(CONTEXT_SUMMARIZE_HEADLINE, {})

        context_window = result.output["context_window"]
        self.assertEqual(context_window[0]["kind"], "parameter")
        self.assertEqual(context_window[-1]["kind"], "tool_result")
        self.assertEqual(context_window[-1]["tool_key"], CONTEXT_SUMMARIZE_HEADLINE)
        self.assertEqual(context_window[-1]["output"]["summary"], "summarized transcript")
        self.assertEqual(len(self.runtime.subcalls), 1)

    def test_truncate_prepends_drop_marker_and_keeps_tail(self) -> None:
        result = self.registry.execute(CONTEXT_STRUCT_TRUNCATE, {"keep_last": 2})

        transcript = result.output["context_window"][1:]
        self.assertEqual(transcript[0]["kind"], "context")
        self.assertIn("entries dropped by truncate", transcript[0]["content"])
        self.assertEqual(len(transcript), 3)

    def test_promote_and_strip_writes_memory_field_and_removes_transcript_entry(self) -> None:
        result = self.registry.execute(
            CONTEXT_SELECT_PROMOTE_AND_STRIP,
            {
                "entry_index": 1,
                "target_field": "continuation_pointer",
                "update_rule": "overwrite",
            },
        )

        self.assertIn("browser.search_jobs", str(self.runtime.state.memory_fields["continuation_pointer"]))
        transcript_entries = [entry for entry in result.output["context_window"] if entry["kind"] != "parameter"]
        self.assertEqual(len(transcript_entries), 3)
        self.assertEqual(self.runtime.save_calls, 1)
        self.assertEqual(self.runtime.refresh_calls, 1)

    def test_inject_section_persists_and_refreshes_parameters(self) -> None:
        result = self.registry.execute(
            CONTEXT_PARAM_INJECT_SECTION,
            {
                "section_label": "Runtime Note",
                "content": "Injected guidance.",
                "position": "last",
            },
        )

        self.assertEqual(result.output["section_label"], "Runtime Note")
        self.assertEqual(self.runtime.save_calls, 1)
        self.assertEqual(self.runtime.refresh_calls, 1)
        context_window = self.runtime.build_context_window()
        self.assertEqual(context_window[1]["label"], "Runtime Note")

    def test_assistant_note_appends_synthetic_assistant_entry(self) -> None:
        result = self.registry.execute(
            CONTEXT_INJECT_ASSISTANT_NOTE,
            {"content": "Next step is validation.", "note_type": "plan"},
        )

        self.assertEqual(result.output["context_window"][-1]["kind"], "assistant")
        self.assertIn("[PLAN]", result.output["context_window"][-1]["content"])

    def test_checkpoint_persists_window_without_modifying_it(self) -> None:
        context_window_before = self.runtime.build_context_window()
        result = self.registry.execute(
            CONTEXT_SELECT_CHECKPOINT,
            {"checkpoint_name": "phase-one", "description": "Before validation"},
        )

        checkpoint_key = result.output["checkpoint_key"]
        self.assertIn(checkpoint_key, self.runtime.state.checkpoints)
        self.assertEqual(result.output["context_window"], context_window_before)


if __name__ == "__main__":
    unittest.main()
