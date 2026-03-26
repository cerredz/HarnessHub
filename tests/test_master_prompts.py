"""Tests for the artifact-backed master prompt registry and public API."""

from __future__ import annotations

from pathlib import Path
import unittest

from harnessiq.master_prompts import (
    MasterPrompt,
    MasterPromptRegistry,
    get_prompt,
    get_prompt_text,
    has_prompt,
    list_prompt_keys,
    list_prompts,
)


ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = ROOT / "artifacts" / "prompts"
REGISTRY_PATH = PROMPTS_DIR / "registry.json"
LEGACY_PROMPTS_DIR = ROOT / "harnessiq" / "master_prompts" / "prompts"

EXPECTED_PROMPT_KEYS = {
    "answer_with_notable_web_sources",
    "autonomous_execution_loop",
    "create_github_execution_issues",
    "create_jira_execution_tickets",
    "create_linear_execution_tickets",
    "create_master_prompts",
    "create_tickets",
    "highest_form_of_leverage",
    "hybrid_academic_and_web_research",
    "implement_and_critique_solutions",
    "mission_driven",
    "parallel_problem_decomposition",
    "phased_code_review",
    "principal_software_engineer_design_patterns",
    "research_with_arxiv_papers",
    "research_with_hugging_face_hub_pages",
    "research_with_hugging_face_papers",
    "spawn_specialized_subagents",
    "surgical_bugfix",
}
STANDARD_STRUCTURE_PROMPT_KEYS = EXPECTED_PROMPT_KEYS - {"mission_driven"}
REQUIRED_PROMPT_SECTIONS = (
    "Identity",
    "Goal",
    "Checklist",
    "Things Not To Do",
    "Success Criteria",
    "Artifacts",
    "Inputs",
)
MISSION_DRIVEN_REQUIRED_SECTIONS = (
    "Identity / Persona",
    "Goal",
    "Component Reference",
    "Storage Layout",
    "Checklist",
    "Things Not To Do",
    "Success Criteria",
    "Inputs",
)


class MasterPromptDataclassTests(unittest.TestCase):
    def test_master_prompt_is_frozen(self) -> None:
        prompt = MasterPrompt(key="k", title="T", description="D", prompt="P")

        with self.assertRaises(AttributeError):
            prompt.key = "other"  # type: ignore[misc]

    def test_master_prompt_fields_are_accessible(self) -> None:
        prompt = MasterPrompt(key="my_key", title="My Title", description="My Desc", prompt="My Prompt")

        self.assertEqual(prompt.key, "my_key")
        self.assertEqual(prompt.title, "My Title")
        self.assertEqual(prompt.description, "My Desc")
        self.assertEqual(prompt.prompt, "My Prompt")


class ArtifactBackedRegistryTests(unittest.TestCase):
    def test_prompt_artifacts_exist(self) -> None:
        self.assertTrue(PROMPTS_DIR.exists())
        self.assertTrue(REGISTRY_PATH.exists())

    def test_legacy_json_prompt_payloads_are_removed(self) -> None:
        self.assertEqual(list(LEGACY_PROMPTS_DIR.glob("*.json")), [])

    def test_registry_lists_all_expected_prompt_keys(self) -> None:
        registry = MasterPromptRegistry()

        self.assertEqual({prompt.key for prompt in registry.list()}, EXPECTED_PROMPT_KEYS)

    def test_registry_returns_sorted_prompt_keys(self) -> None:
        registry = MasterPromptRegistry()

        keys = registry.keys()

        self.assertEqual(keys, sorted(keys))
        self.assertEqual(set(keys), EXPECTED_PROMPT_KEYS)

    def test_registry_prompts_are_backed_by_markdown_files(self) -> None:
        registry = MasterPromptRegistry()

        for prompt in registry.list():
            with self.subTest(prompt=prompt.key):
                artifact_path = PROMPTS_DIR / f"{prompt.key}.md"
                self.assertTrue(artifact_path.exists())
                self.assertEqual(prompt.prompt, artifact_path.read_text(encoding="utf-8"))

    def test_registry_provides_non_empty_metadata(self) -> None:
        registry = MasterPromptRegistry()

        for prompt in registry.list():
            with self.subTest(prompt=prompt.key):
                self.assertTrue(prompt.title.strip())
                self.assertTrue(prompt.description.strip())
                self.assertTrue(prompt.prompt.strip())

    def test_get_unknown_prompt_raises_key_error(self) -> None:
        registry = MasterPromptRegistry()

        with self.assertRaises(KeyError):
            registry.get("this_key_does_not_exist")


class PromptStructureTests(unittest.TestCase):
    def test_standard_prompts_include_core_sections(self) -> None:
        registry = MasterPromptRegistry()

        for key in STANDARD_STRUCTURE_PROMPT_KEYS:
            with self.subTest(prompt=key):
                prompt_text = registry.get_prompt_text(key)
                for section_name in REQUIRED_PROMPT_SECTIONS:
                    self.assertIn(section_name, prompt_text)

    def test_mission_driven_prompt_contains_expected_sections(self) -> None:
        prompt_text = MasterPromptRegistry().get_prompt_text("mission_driven")

        for section_name in MISSION_DRIVEN_REQUIRED_SECTIONS:
            with self.subTest(section=section_name):
                self.assertIn(section_name, prompt_text)


class ModuleLevelApiTests(unittest.TestCase):
    def test_get_prompt_returns_master_prompt(self) -> None:
        prompt = get_prompt("create_master_prompts")

        self.assertIsInstance(prompt, MasterPrompt)
        self.assertEqual(prompt.key, "create_master_prompts")

    def test_get_prompt_text_matches_prompt_field(self) -> None:
        self.assertEqual(
            get_prompt_text("create_master_prompts"),
            get_prompt("create_master_prompts").prompt,
        )

    def test_list_prompts_returns_expected_catalog(self) -> None:
        prompts = list_prompts()

        self.assertGreaterEqual(len(prompts), len(EXPECTED_PROMPT_KEYS))
        self.assertEqual({prompt.key for prompt in prompts}, EXPECTED_PROMPT_KEYS)

    def test_list_prompt_keys_returns_expected_catalog(self) -> None:
        self.assertEqual(set(list_prompt_keys()), EXPECTED_PROMPT_KEYS)

    def test_has_prompt_reports_presence(self) -> None:
        self.assertTrue(has_prompt("create_master_prompts"))
        self.assertFalse(has_prompt("nonexistent_key_xyz"))

    def test_harnessiq_master_prompts_is_available_from_top_level_import(self) -> None:
        import harnessiq

        prompt = harnessiq.master_prompts.get_prompt("create_master_prompts")

        self.assertIsInstance(prompt, MasterPrompt)


if __name__ == "__main__":
    unittest.main()
