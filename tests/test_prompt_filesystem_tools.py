"""Tests for prompt-generation and filesystem tools."""

from __future__ import annotations

import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from harnessiq.shared.tools import FILESYSTEM_PATH_EXISTS, PROMPT_CREATE_SYSTEM_PROMPT
from harnessiq.tools import (
    append_text_file,
    copy_path,
    create_builtin_registry,
    create_system_prompt,
    get_current_directory,
    list_directory,
    make_directory,
    path_exists,
    read_text_file,
    write_text_file,
)


class PromptAndFilesystemToolsTests(unittest.TestCase):
    def test_create_system_prompt_uses_inputs_and_context(self) -> None:
        prompt = create_system_prompt(
            "research assistant",
            "Produce a concise hardware launch brief.",
            [
                {"kind": "parameter", "label": "Identity", "content": "Helpful and exact."},
                {"kind": "message", "role": "user", "content": "Find the latest GPU release timeline."},
                {"kind": "summary", "content": "The user cares about verified dates only."},
            ],
            agent_name="Scout",
            tone="precise",
            instructions=["Check all claims against tool outputs."],
            constraints=["Do not invent dates."],
            available_tools=[{"name": "browser.search", "description": "Search the web."}],
            max_context_entries=2,
        )

        self.assertIn("You are Scout, a research assistant.", prompt)
        self.assertIn("Use a precise tone.", prompt)
        self.assertIn("[PRIMARY OBJECTIVE]", prompt)
        self.assertIn("Produce a concise hardware launch brief.", prompt)
        self.assertIn("Check all claims against tool outputs.", prompt)
        self.assertIn("Do not invent dates.", prompt)
        self.assertIn("browser.search: Search the web.", prompt)
        self.assertIn("Identity: Helpful and exact.", prompt)
        self.assertIn("Summary: The user cares about verified dates only.", prompt)

    def test_create_system_prompt_limits_recent_context_entries(self) -> None:
        prompt = create_system_prompt(
            "operator",
            "Keep the run on track.",
            [
                {"kind": "message", "role": "user", "content": "first"},
                {"kind": "message", "role": "assistant", "content": "second"},
                {"kind": "summary", "content": "third"},
            ],
            max_context_entries=1,
        )

        self.assertNotIn("first", prompt)
        self.assertNotIn("second", prompt)
        self.assertIn("third", prompt)

    def test_create_system_prompt_rejects_blank_role(self) -> None:
        with self.assertRaisesRegex(ValueError, "role must not be empty"):
            create_system_prompt("   ", "Objective", [])

    def test_get_current_directory_matches_process_directory(self) -> None:
        self.assertEqual(get_current_directory(), os.getcwd())

    def test_filesystem_helpers_support_non_destructive_text_workflow(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            notes_path = root / "notes.txt"
            archive_dir = root / "archive"
            copied_path = archive_dir / "notes-copy.txt"

            write_result = write_text_file(str(notes_path), "hello")
            append_result = append_text_file(str(notes_path), " world")
            read_result = read_text_file(str(notes_path))
            mkdir_result = make_directory(str(archive_dir))
            copy_result = copy_path(str(notes_path), str(copied_path))
            listing = list_directory(str(root))
            existence = path_exists(str(copied_path))

            self.assertTrue(write_result["created"])
            self.assertFalse(append_result["created"])
            self.assertEqual(read_result["content"], "hello world")
            self.assertTrue(mkdir_result["created"])
            self.assertEqual(copy_result["copied_type"], "file")
            self.assertEqual([entry["name"] for entry in listing], ["archive", "notes.txt"])
            self.assertTrue(existence["exists"])
            self.assertTrue(existence["is_file"])

    def test_write_text_file_refuses_overwrite(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            target = Path(tmp_dir) / "existing.txt"
            target.write_text("old", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "overwriting is not allowed"):
                write_text_file(str(target), "new")

    def test_registry_executes_prompt_and_filesystem_tools(self) -> None:
        registry = create_builtin_registry()
        with TemporaryDirectory() as tmp_dir:
            temp_path = Path(tmp_dir) / "missing.txt"
            prompt_result = registry.execute(
                PROMPT_CREATE_SYSTEM_PROMPT,
                {
                    "role": "planner",
                    "objective": "Make a tight plan.",
                    "context_window": [{"kind": "summary", "content": "A bug report is pending."}],
                },
            )
            path_result = registry.execute(FILESYSTEM_PATH_EXISTS, {"path": str(temp_path)})

        self.assertIn("Make a tight plan.", prompt_result.output["system_prompt"])
        self.assertFalse(path_result.output["exists"])


if __name__ == "__main__":
    unittest.main()

