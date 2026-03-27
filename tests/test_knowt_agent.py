"""Tests for the KnowtAgent harness."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Sequence
from unittest.mock import MagicMock, patch

from harnessiq.agents import KnowtAgent, KnowtMemoryStore
from harnessiq.shared.agents import AgentModelResponse, AgentParameterSection, AgentRuntimeConfig
from harnessiq.shared.exceptions import ResourceNotFoundError
from harnessiq.shared.knowt import KnowtAgentConfig
from harnessiq.shared.tools import (
    KNOWT_CREATE_SCRIPT,
    REASON_BRAINSTORM,
    REASON_CHAIN_OF_THOUGHT,
    REASON_CRITIQUE,
    KNOWT_CREATE_AVATAR_DESCRIPTION,
    KNOWT_CREATE_VIDEO,
    FILES_CREATE_FILE,
    FILES_EDIT_FILE,
)

_LANGSMITH_CLIENT_PATCHER = patch("harnessiq.agents.base.agent_helpers.build_langsmith_client", return_value=None)


def setUpModule() -> None:
    _LANGSMITH_CLIENT_PATCHER.start()


def tearDownModule() -> None:
    _LANGSMITH_CLIENT_PATCHER.stop()


def _mock_model(*, message: str = "Done.", tool_calls: tuple = (), should_continue: bool = False) -> MagicMock:
    model = MagicMock()
    model.generate_turn.return_value = AgentModelResponse(
        assistant_message=message,
        tool_calls=tool_calls,
        should_continue=should_continue,
    )
    return model


class TestKnowtAgentImport(unittest.TestCase):
    """Verify the public API is importable from the agents package."""

    def test_knowt_agent_importable(self) -> None:
        from harnessiq.agents import KnowtAgent  # noqa: F401

    def test_knowt_memory_store_importable(self) -> None:
        from harnessiq.agents import KnowtMemoryStore  # noqa: F401


class TestKnowtAgentInitialization(unittest.TestCase):
    """Verify correct construction and wiring."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.model = _mock_model()

    def test_instantiates_with_model_and_memory_path(self) -> None:
        agent = KnowtAgent(model=self.model, memory_path=self.tmp)
        self.assertIsNotNone(agent)

    def test_name_is_knowt_content_creator(self) -> None:
        agent = KnowtAgent(model=self.model, memory_path=self.tmp)
        self.assertEqual(agent.name, "knowt_content_creator")

    def test_memory_store_is_prepared_after_init(self) -> None:
        agent = KnowtAgent(model=self.model, memory_path=self.tmp)
        self.assertTrue((Path(self.tmp) / "current_script.md").exists())
        self.assertTrue((Path(self.tmp) / "current_avatar_description.md").exists())

    def test_config_reflects_constructor_arguments(self) -> None:
        agent = KnowtAgent(model=self.model, memory_path=self.tmp, max_tokens=40_000, reset_threshold=0.8)
        self.assertEqual(agent.config.max_tokens, 40_000)
        self.assertAlmostEqual(agent.config.reset_threshold, 0.8)

    def test_memory_store_property_returns_correct_type(self) -> None:
        agent = KnowtAgent(model=self.model, memory_path=self.tmp)
        self.assertIsInstance(agent.memory_store, KnowtMemoryStore)

    def test_memory_path_as_string_accepted(self) -> None:
        agent = KnowtAgent(model=self.model, memory_path=str(self.tmp))
        self.assertIsNotNone(agent)


class TestKnowtAgentSystemPrompt(unittest.TestCase):
    """Verify prompt loading behavior."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.model = _mock_model()

    def test_build_system_prompt_returns_non_empty_string(self) -> None:
        agent = KnowtAgent(model=self.model, memory_path=self.tmp)
        prompt = agent.build_system_prompt()
        self.assertIsInstance(prompt, str)
        self.assertTrue(len(prompt) > 0)

    def test_prompt_contains_key_sections(self) -> None:
        agent = KnowtAgent(model=self.model, memory_path=self.tmp)
        prompt = agent.build_system_prompt()
        self.assertIn("Agent Guide", prompt)
        self.assertIn("Operating Rules", prompt)
        self.assertIn("Agent Memory", prompt)
        self.assertIn("Environment", prompt)

    def test_prompt_contains_todo_placeholders(self) -> None:
        agent = KnowtAgent(model=self.model, memory_path=self.tmp)
        prompt = agent.build_system_prompt()
        self.assertIn("[TODO:", prompt)

    def test_prompt_loaded_from_file(self) -> None:
        """Overwriting the prompt file must change the returned prompt."""
        from harnessiq.agents.knowt.agent import _MASTER_PROMPT_PATH
        original = _MASTER_PROMPT_PATH.read_text(encoding="utf-8")
        try:
            _MASTER_PROMPT_PATH.write_text("Custom prompt for test.", encoding="utf-8")
            agent = KnowtAgent(model=self.model, memory_path=self.tmp)
            self.assertEqual(agent.build_system_prompt(), "Custom prompt for test.")
        finally:
            _MASTER_PROMPT_PATH.write_text(original, encoding="utf-8")

    def test_missing_prompt_file_raises_file_not_found(self) -> None:
        from harnessiq.agents.knowt import agent as agent_module
        original = agent_module._MASTER_PROMPT_PATH
        try:
            agent_module._MASTER_PROMPT_PATH = Path(self.tmp) / "nonexistent.md"
            knowt = KnowtAgent(model=self.model, memory_path=self.tmp)
            with self.assertRaises(ResourceNotFoundError) as raised:
                knowt.build_system_prompt()
            self.assertIsInstance(raised.exception, FileNotFoundError)
        finally:
            agent_module._MASTER_PROMPT_PATH = original


class TestKnowtAgentParameterSections(unittest.TestCase):
    """Verify load_parameter_sections output."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.model = _mock_model()
        self.agent = KnowtAgent(model=self.model, memory_path=self.tmp)

    def test_returns_two_sections(self) -> None:
        sections = self.agent.load_parameter_sections()
        self.assertEqual(len(sections), 2)

    def test_section_titles(self) -> None:
        sections = self.agent.load_parameter_sections()
        titles = [s.title for s in sections]
        self.assertIn("Current Script", titles)
        self.assertIn("Current Avatar Description", titles)

    def test_placeholder_when_script_not_created(self) -> None:
        sections = {s.title: s.content for s in self.agent.load_parameter_sections()}
        self.assertIn("no script", sections["Current Script"].lower())

    def test_placeholder_when_avatar_description_not_created(self) -> None:
        sections = {s.title: s.content for s in self.agent.load_parameter_sections()}
        self.assertIn("no avatar", sections["Current Avatar Description"].lower())

    def test_actual_script_content_when_present(self) -> None:
        self.agent.memory_store.write_script("My TikTok script text.")
        sections = {s.title: s.content for s in self.agent.load_parameter_sections()}
        self.assertIn("My TikTok script text.", sections["Current Script"])

    def test_actual_avatar_content_when_present(self) -> None:
        self.agent.memory_store.write_avatar_description("Young professional, energetic.")
        sections = {s.title: s.content for s in self.agent.load_parameter_sections()}
        self.assertIn("Young professional", sections["Current Avatar Description"])


class TestKnowtAgentAvailableTools(unittest.TestCase):
    """Verify the agent's tool registry contains all expected tools."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.agent = KnowtAgent(model=_mock_model(), memory_path=self.tmp)

    def _tool_keys(self) -> set[str]:
        return {t.key for t in self.agent.available_tools()}

    def test_contains_all_reasoning_tools(self) -> None:
        keys = self._tool_keys()
        self.assertIn(REASON_BRAINSTORM, keys)
        self.assertIn(REASON_CHAIN_OF_THOUGHT, keys)
        self.assertIn(REASON_CRITIQUE, keys)

    def test_contains_all_knowt_tools(self) -> None:
        keys = self._tool_keys()
        self.assertIn(KNOWT_CREATE_SCRIPT, keys)
        self.assertIn(KNOWT_CREATE_AVATAR_DESCRIPTION, keys)
        self.assertIn(KNOWT_CREATE_VIDEO, keys)
        self.assertIn(FILES_CREATE_FILE, keys)
        self.assertIn(FILES_EDIT_FILE, keys)

    def test_total_tool_count_is_eight(self) -> None:
        # 3 reasoning + 5 knowt
        self.assertEqual(len(self.agent.available_tools()), 8)

    def test_inspect_tools_is_inherited_from_base_agent(self) -> None:
        payload = self.agent.inspect_tools()
        tool_index = {tool["key"]: tool for tool in payload}

        self.assertIn(REASON_BRAINSTORM, tool_index)
        self.assertIn(KNOWT_CREATE_SCRIPT, tool_index)
        self.assertIn("function", tool_index[REASON_BRAINSTORM])
        self.assertIsInstance(tool_index[KNOWT_CREATE_SCRIPT]["parameters"], list)


class TestKnowtAgentInjection(unittest.TestCase):
    """Verify injectable config and tools parameters."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.model = _mock_model()

    def test_injected_config_overrides_scalar_params(self) -> None:
        config = KnowtAgentConfig(memory_path=Path(self.tmp), max_tokens=99_000, reset_threshold=0.9)
        agent = KnowtAgent(model=self.model, memory_path=self.tmp, config=config)
        self.assertEqual(agent.config.max_tokens, 99_000)
        self.assertAlmostEqual(agent.config.reset_threshold, 0.9)

    def test_injected_config_takes_precedence_over_scalar_params(self) -> None:
        config = KnowtAgentConfig(memory_path=Path(self.tmp), max_tokens=55_000)
        agent = KnowtAgent(model=self.model, memory_path=self.tmp, max_tokens=10_000, config=config)
        self.assertEqual(agent.config.max_tokens, 55_000)

    def test_injected_tools_are_added_to_defaults(self) -> None:
        from harnessiq.shared.tools import RegisteredTool, ToolDefinition
        stub = RegisteredTool(
            definition=ToolDefinition(
                key="custom.stub",
                name="stub",
                description="A stub tool.",
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            ),
            handler=lambda args: {},
        )
        agent = KnowtAgent(model=self.model, memory_path=self.tmp, tools=[stub])
        keys = {t.key for t in agent.available_tools()}
        self.assertIn("custom.stub", keys)
        self.assertIn(REASON_BRAINSTORM, keys)

    def test_memory_path_exposed_on_base_agent(self) -> None:
        agent = KnowtAgent(model=self.model, memory_path=self.tmp)
        self.assertEqual(agent.memory_path, Path(self.tmp))

    def test_runtime_config_preserves_langsmith_settings(self) -> None:
        agent = KnowtAgent(
            model=self.model,
            memory_path=self.tmp,
            runtime_config=AgentRuntimeConfig(
                langsmith_api_key="ls_test_sdk",
                langsmith_project="knowt-project",
            ),
        )
        self.assertEqual(agent.runtime_config.langsmith_api_key, "ls_test_sdk")
        self.assertEqual(agent.runtime_config.langsmith_project, "knowt-project")


class TestKnowtAgentRunLoop(unittest.TestCase):
    """Verify the agent can run a simple loop to completion."""

    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()

    def test_run_completes_when_model_signals_stop(self) -> None:
        model = _mock_model(message="All done.", should_continue=False)
        agent = KnowtAgent(model=model, memory_path=self.tmp)
        result = agent.run(max_cycles=1)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.cycles_completed, 1)

    def test_run_respects_max_cycles(self) -> None:
        model = _mock_model(message="Still going.", should_continue=True)
        agent = KnowtAgent(model=model, memory_path=self.tmp)
        result = agent.run(max_cycles=3)
        self.assertEqual(result.status, "max_cycles_reached")
        self.assertEqual(result.cycles_completed, 3)


if __name__ == "__main__":
    unittest.main()
