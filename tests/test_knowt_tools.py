"""Tests for the Knowt content-creation tools."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any, Mapping
from unittest.mock import MagicMock

from harnessiq.shared.dtos import PreparedProviderOperationResultDTO, ProviderOperationRequestDTO
from harnessiq.shared.knowt import KnowtMemoryStore
from harnessiq.shared.tools import (
    FILES_CREATE_FILE,
    FILES_EDIT_FILE,
    KNOWT_CREATE_AVATAR_DESCRIPTION,
    KNOWT_CREATE_SCRIPT,
    KNOWT_CREATE_VIDEO,
)
from harnessiq.tools.knowt import create_knowt_tools
from harnessiq.tools.registry import ToolRegistry, ToolValidationError


def _make_store(tmp_path: Path) -> KnowtMemoryStore:
    store = KnowtMemoryStore(tmp_path)
    store.prepare()
    return store


def _make_mock_client(response: Any = None) -> MagicMock:
    client = MagicMock()
    client.execute_operation.return_value = PreparedProviderOperationResultDTO(
        operation="create_lipsync_v2",
        method="POST",
        path="/v2/lipsync",
        response=response or {"id": "video-abc123", "status": "pending"},
    )
    return client


class TestKnowtToolsFactory(unittest.TestCase):
    """Verify factory output and registry integration."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.store = _make_store(Path(self.tmp))
        self.tools = create_knowt_tools(memory_store=self.store)

    def test_factory_returns_five_tools(self) -> None:
        self.assertEqual(len(self.tools), 5)

    def test_factory_returns_stable_key_order(self) -> None:
        keys = tuple(t.key for t in self.tools)
        self.assertEqual(
            keys,
            (
                KNOWT_CREATE_SCRIPT,
                KNOWT_CREATE_AVATAR_DESCRIPTION,
                KNOWT_CREATE_VIDEO,
                FILES_CREATE_FILE,
                FILES_EDIT_FILE,
            ),
        )

    def test_tools_register_without_conflict(self) -> None:
        registry = ToolRegistry(self.tools)
        for key in (KNOWT_CREATE_SCRIPT, KNOWT_CREATE_AVATAR_DESCRIPTION, KNOWT_CREATE_VIDEO, FILES_CREATE_FILE, FILES_EDIT_FILE):
            self.assertIn(key, registry)

    def test_all_schemas_disallow_additional_properties(self) -> None:
        for tool in self.tools:
            self.assertFalse(
                tool.definition.input_schema.get("additionalProperties", True),
                f"{tool.key} should have additionalProperties=False",
            )

    def test_constants_exported_from_shared_tools(self) -> None:
        self.assertEqual(KNOWT_CREATE_SCRIPT, "knowt.create_script")
        self.assertEqual(KNOWT_CREATE_AVATAR_DESCRIPTION, "knowt.create_avatar_description")
        self.assertEqual(KNOWT_CREATE_VIDEO, "knowt.create_video")
        self.assertEqual(FILES_CREATE_FILE, "files.create_file")
        self.assertEqual(FILES_EDIT_FILE, "files.edit_file")


class TestCreateScriptTool(unittest.TestCase):
    """Unit tests for knowt.create_script."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.store = _make_store(Path(self.tmp))
        self.registry = ToolRegistry(create_knowt_tools(memory_store=self.store))

    def test_stores_script_in_memory(self) -> None:
        self.registry.execute(KNOWT_CREATE_SCRIPT, {
            "topic": "Study tips",
            "angle": "3-minute rule",
            "script_text": "Hook: Did you know you can master anything in 3 minutes?",
        })
        self.assertTrue(self.store.is_script_created())
        self.assertIn("3 minutes", self.store.read_script())

    def test_returns_script_and_metadata(self) -> None:
        result = self.registry.execute(KNOWT_CREATE_SCRIPT, {
            "topic": "Flashcards",
            "angle": "spaced repetition",
            "script_text": "Learn faster with spaced repetition.",
        })
        output = result.output
        self.assertEqual(output["topic"], "Flashcards")
        self.assertEqual(output["angle"], "spaced repetition")
        self.assertIn("Learn faster", output["script"])
        self.assertIn("stored_to", output)

    def test_appends_to_creation_log(self) -> None:
        self.registry.execute(KNOWT_CREATE_SCRIPT, {
            "topic": "Mnemonics",
            "angle": "acronyms",
            "script_text": "Memory tricks work.",
        })
        log = self.store.read_creation_log()
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0].action, "create_script")

    def test_missing_required_fields_raises(self) -> None:
        with self.assertRaises(ToolValidationError):
            self.registry.execute(KNOWT_CREATE_SCRIPT, {"topic": "only topic"})

    def test_empty_script_text_raises(self) -> None:
        with self.assertRaises(Exception):
            self.registry.execute(KNOWT_CREATE_SCRIPT, {
                "topic": "t", "angle": "a", "script_text": ""
            })


class TestCreateAvatarDescriptionTool(unittest.TestCase):
    """Unit tests for knowt.create_avatar_description."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.store = _make_store(Path(self.tmp))
        self.registry = ToolRegistry(create_knowt_tools(memory_store=self.store))

    def test_stores_avatar_description_in_memory(self) -> None:
        self.registry.execute(KNOWT_CREATE_AVATAR_DESCRIPTION, {
            "script_text": "Study smarter with Knowt flashcards.",
            "avatar_style": "friendly educator",
        })
        self.assertTrue(self.store.is_avatar_description_created())

    def test_returns_chain_of_thought_and_description(self) -> None:
        result = self.registry.execute(KNOWT_CREATE_AVATAR_DESCRIPTION, {
            "script_text": "Master vocabulary with spaced repetition.",
            "avatar_style": "energetic coach",
            "target_audience": "high school students",
            "tone": "enthusiastic",
        })
        output = result.output
        self.assertIn("chain_of_thought", output)
        self.assertIn("avatar_description", output)
        self.assertIn("stored_to", output)
        self.assertIn("[AVATAR REASONING]", output["chain_of_thought"])

    def test_avatar_description_includes_style(self) -> None:
        self.registry.execute(KNOWT_CREATE_AVATAR_DESCRIPTION, {
            "script_text": "Text to ingest.",
            "avatar_style": "calm professor",
        })
        description = self.store.read_avatar_description()
        self.assertIn("calm professor", description.lower())

    def test_optional_fields_reflected_in_output(self) -> None:
        result = self.registry.execute(KNOWT_CREATE_AVATAR_DESCRIPTION, {
            "script_text": "Some script.",
            "avatar_style": "relatable peer",
            "target_audience": "college students",
            "tone": "casual and warm",
        })
        output = result.output["chain_of_thought"]
        self.assertIn("college students", output)
        self.assertIn("casual and warm", output)

    def test_appends_to_creation_log(self) -> None:
        self.registry.execute(KNOWT_CREATE_AVATAR_DESCRIPTION, {
            "script_text": "Script.", "avatar_style": "mentor"
        })
        log = self.store.read_creation_log()
        self.assertEqual(len(log), 1)
        self.assertEqual(log[0].action, "create_avatar_description")

    def test_missing_required_fields_raises(self) -> None:
        with self.assertRaises(ToolValidationError):
            self.registry.execute(KNOWT_CREATE_AVATAR_DESCRIPTION, {"script_text": "text only"})


class TestCreateVideoTool(unittest.TestCase):
    """Unit tests for knowt.create_video — memory guard and Creatify integration."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.store = _make_store(Path(self.tmp))

    def _registry_without_client(self) -> ToolRegistry:
        return ToolRegistry(create_knowt_tools(memory_store=self.store))

    def _registry_with_client(self, client: MagicMock) -> ToolRegistry:
        return ToolRegistry(create_knowt_tools(memory_store=self.store, creatify_client=client))

    def _fill_prerequisites(self) -> None:
        self.store.write_script("Full TikTok script text.")
        self.store.write_avatar_description("Young professional, energetic.")

    def test_returns_error_dict_when_no_script_or_avatar(self) -> None:
        registry = self._registry_without_client()
        result = registry.execute(KNOWT_CREATE_VIDEO, {
            "script": "text", "avatar_id": "av1", "voice_id": "v1"
        })
        output = result.output
        self.assertIn("error", output)
        self.assertIn("missing", output)
        self.assertIn("create_script", output["missing"])
        self.assertIn("create_avatar_description", output["missing"])

    def test_returns_error_dict_when_only_script_missing(self) -> None:
        self.store.write_avatar_description("Avatar desc.")
        registry = self._registry_without_client()
        result = registry.execute(KNOWT_CREATE_VIDEO, {
            "script": "text", "avatar_id": "av1", "voice_id": "v1"
        })
        output = result.output
        self.assertIn("create_script", output["missing"])
        self.assertNotIn("create_avatar_description", output["missing"])

    def test_returns_error_dict_when_only_avatar_missing(self) -> None:
        self.store.write_script("Script text.")
        registry = self._registry_without_client()
        result = registry.execute(KNOWT_CREATE_VIDEO, {
            "script": "text", "avatar_id": "av1", "voice_id": "v1"
        })
        output = result.output
        self.assertIn("create_avatar_description", output["missing"])
        self.assertNotIn("create_script", output["missing"])

    def test_returns_error_dict_when_no_creatify_client(self) -> None:
        self._fill_prerequisites()
        registry = self._registry_without_client()
        result = registry.execute(KNOWT_CREATE_VIDEO, {
            "script": "text", "avatar_id": "av1", "voice_id": "v1"
        })
        output = result.output
        self.assertIn("error", output)
        self.assertIn("Creatify", output["error"])

    def test_calls_creatify_create_lipsync_v2_when_prerequisites_met(self) -> None:
        self._fill_prerequisites()
        mock_client = _make_mock_client()
        registry = self._registry_with_client(mock_client)
        result = registry.execute(KNOWT_CREATE_VIDEO, {
            "script": "The actual script.", "avatar_id": "av-123", "voice_id": "vo-456"
        })
        mock_client.execute_operation.assert_called_once()
        request = mock_client.execute_operation.call_args.args[0]
        self.assertIsInstance(request, ProviderOperationRequestDTO)
        payload = request.payload
        self.assertEqual(request.operation, "create_lipsync_v2")
        self.assertEqual(payload["script"], "The actual script.")
        self.assertEqual(payload["avatar_id"], "av-123")
        self.assertEqual(payload["voice_id"], "vo-456")
        self.assertEqual(payload["aspect_ratio"], "9:16")

    def test_default_aspect_ratio_is_tiktok(self) -> None:
        self._fill_prerequisites()
        mock_client = _make_mock_client()
        registry = self._registry_with_client(mock_client)
        registry.execute(KNOWT_CREATE_VIDEO, {
            "script": "s", "avatar_id": "a", "voice_id": "v"
        })
        payload = mock_client.execute_operation.call_args.args[0].payload
        self.assertEqual(payload["aspect_ratio"], "9:16")

    def test_custom_aspect_ratio_passed_to_api(self) -> None:
        self._fill_prerequisites()
        mock_client = _make_mock_client()
        registry = self._registry_with_client(mock_client)
        registry.execute(KNOWT_CREATE_VIDEO, {
            "script": "s", "avatar_id": "a", "voice_id": "v", "aspect_ratio": "1:1"
        })
        payload = mock_client.execute_operation.call_args.args[0].payload
        self.assertEqual(payload["aspect_ratio"], "1:1")

    def test_optional_name_and_background_url_passed_when_provided(self) -> None:
        self._fill_prerequisites()
        mock_client = _make_mock_client()
        registry = self._registry_with_client(mock_client)
        registry.execute(KNOWT_CREATE_VIDEO, {
            "script": "s", "avatar_id": "a", "voice_id": "v",
            "name": "My Video", "background_url": "https://example.com/bg.jpg"
        })
        payload = mock_client.execute_operation.call_args.args[0].payload
        self.assertEqual(payload["name"], "My Video")
        self.assertEqual(payload["background_url"], "https://example.com/bg.jpg")

    def test_optional_fields_absent_when_not_provided(self) -> None:
        self._fill_prerequisites()
        mock_client = _make_mock_client()
        registry = self._registry_with_client(mock_client)
        registry.execute(KNOWT_CREATE_VIDEO, {
            "script": "s", "avatar_id": "a", "voice_id": "v"
        })
        payload = mock_client.execute_operation.call_args.args[0].payload
        self.assertNotIn("name", payload)
        self.assertNotIn("background_url", payload)

    def test_returns_operation_name_and_response(self) -> None:
        self._fill_prerequisites()
        mock_client = _make_mock_client({"id": "vid-xyz", "status": "pending"})
        registry = self._registry_with_client(mock_client)
        result = registry.execute(KNOWT_CREATE_VIDEO, {
            "script": "s", "avatar_id": "a", "voice_id": "v"
        })
        output = result.output
        self.assertEqual(output["operation"], "create_lipsync_v2")
        self.assertEqual(output["response"]["id"], "vid-xyz")

    def test_appends_to_creation_log_on_success(self) -> None:
        self._fill_prerequisites()
        mock_client = _make_mock_client()
        registry = self._registry_with_client(mock_client)
        registry.execute(KNOWT_CREATE_VIDEO, {
            "script": "s", "avatar_id": "a", "voice_id": "v"
        })
        log = self.store.read_creation_log()
        self.assertTrue(any(e.action == "create_video" for e in log))

    def test_error_dict_not_exception_on_missing_prerequisites(self) -> None:
        """Guard must return a dict, not raise, so BaseAgent records it normally."""
        registry = self._registry_without_client()
        result = registry.execute(KNOWT_CREATE_VIDEO, {
            "script": "s", "avatar_id": "a", "voice_id": "v"
        })
        self.assertIsInstance(result.output, dict)


class TestCreateFileTool(unittest.TestCase):
    """Unit tests for knowt.create_file."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.store = _make_store(Path(self.tmp))
        self.registry = ToolRegistry(create_knowt_tools(memory_store=self.store))

    def test_creates_file_in_memory_directory(self) -> None:
        self.registry.execute(FILES_CREATE_FILE, {"filename": "notes.md", "content": "my notes"})
        self.assertTrue((Path(self.tmp) / "notes.md").exists())

    def test_returns_action_created(self) -> None:
        result = self.registry.execute(FILES_CREATE_FILE, {"filename": "draft.md", "content": "draft"})
        self.assertEqual(result.output["action"], "created")

    def test_path_traversal_rejected(self) -> None:
        with self.assertRaises(Exception):
            self.registry.execute(FILES_CREATE_FILE, {"filename": "../escape.txt", "content": "bad"})

    def test_missing_filename_raises(self) -> None:
        with self.assertRaises(ToolValidationError):
            self.registry.execute(FILES_CREATE_FILE, {"content": "text"})


class TestEditFileTool(unittest.TestCase):
    """Unit tests for knowt.edit_file."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.store = _make_store(Path(self.tmp))
        self.registry = ToolRegistry(create_knowt_tools(memory_store=self.store))

    def test_overwrites_file_content(self) -> None:
        self.registry.execute(FILES_CREATE_FILE, {"filename": "notes.md", "content": "original"})
        self.registry.execute(FILES_EDIT_FILE, {"filename": "notes.md", "content": "updated"})
        content = self.store.read_file("notes.md").strip()
        self.assertEqual(content, "updated")

    def test_returns_action_edited(self) -> None:
        self.registry.execute(FILES_CREATE_FILE, {"filename": "f.md", "content": "first"})
        result = self.registry.execute(FILES_EDIT_FILE, {"filename": "f.md", "content": "second"})
        self.assertEqual(result.output["action"], "edited")

    def test_path_traversal_rejected(self) -> None:
        with self.assertRaises(Exception):
            self.registry.execute(FILES_EDIT_FILE, {"filename": "../../etc/passwd", "content": "x"})


if __name__ == "__main__":
    unittest.main()
