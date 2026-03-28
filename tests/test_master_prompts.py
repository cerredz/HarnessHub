"""Tests for the master_prompts module - registry, loading, and public API."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from harnessiq.master_prompts import (
    MasterPrompt,
    MasterPromptRegistry,
    get_prompt,
    get_prompt_text,
    has_prompt,
    list_prompt_keys,
    list_prompts,
)


EXPECTED_PROMPT_KEYS = {
    "answer_with_notable_web_sources",
    "autonomous_execution_loop",
    "cognitive_multiplexer",
    "competitor_researcher",
    "create_github_execution_issues",
    "create_jira_execution_tickets",
    "create_linear_execution_tickets",
    "create_master_prompts",
    "create_tickets",
    "highest_form_of_leverage",
    "hybrid_academic_and_web_research",
    "implement_and_critique_solutions",
    "linkedin_job_applier",
    "mission_driven",
    "never_stop",
    "orchestrator_master_prompt",
    "parallel_problem_decomposition",
    "phased_code_review",
    "principal_software_engineer_design_patterns",
    "research_with_arxiv_papers",
    "research_with_hugging_face_hub_pages",
    "research_with_hugging_face_papers",
    "spawn_specialized_subagents",
    "surgical_bugfix",
}
STANDARD_STRUCTURE_PROMPT_KEYS = EXPECTED_PROMPT_KEYS - {
    "cognitive_multiplexer",
    "mission_driven",
    "orchestrator_master_prompt",
}
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
PERSONA_PROMPT_REQUIRED_SECTIONS = (
    "Identity / Persona",
    "Goal",
    "Checklist",
    "Things Not To Do",
    "Success Criteria",
    "Artifacts",
    "Inputs",
)
MASTER_PROMPTS_README = Path(__file__).resolve().parents[1] / "harnessiq" / "master_prompts" / "README.md"


def _section_heading_pattern(section_name: str) -> re.Pattern[str]:
    escaped = re.escape(section_name)
    if section_name == "Identity":
        variants = (escaped, re.escape("Identity / Persona"))
    else:
        variants = (escaped,)
    body = "|".join(variants)
    return re.compile(rf"^(?:##\s+)?(?:{body})\s*$", re.MULTILINE)


def _section_position(prompt_text: str, section_name: str) -> int:
    match = _section_heading_pattern(section_name).search(prompt_text)
    if match is not None:
        return match.start()
    try:
        return prompt_text.index(section_name)
    except ValueError as exc:
        raise AssertionError(f"Missing section heading for {section_name!r}") from exc


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


class MasterPromptRegistryTests(unittest.TestCase):
    def test_list_returns_expected_prompt_count_or_more(self) -> None:
        registry = MasterPromptRegistry()

        prompts = registry.list()

        self.assertGreaterEqual(len(prompts), len(EXPECTED_PROMPT_KEYS))

    def test_list_returns_master_prompt_instances(self) -> None:
        registry = MasterPromptRegistry()

        prompts = registry.list()

        for prompt in prompts:
            self.assertIsInstance(prompt, MasterPrompt)

    def test_list_is_sorted_by_key(self) -> None:
        registry = MasterPromptRegistry()

        prompts = registry.list()
        keys = [p.key for p in prompts]

        self.assertEqual(keys, sorted(keys))

    def test_get_returns_correct_prompt_by_key(self) -> None:
        registry = MasterPromptRegistry()

        prompt = registry.get("create_master_prompts")

        self.assertIsInstance(prompt, MasterPrompt)
        self.assertEqual(prompt.key, "create_master_prompts")

    def test_get_raises_key_error_for_unknown_key(self) -> None:
        registry = MasterPromptRegistry()

        with self.assertRaises(KeyError):
            registry.get("this_key_does_not_exist")

    def test_get_prompt_text_returns_string(self) -> None:
        registry = MasterPromptRegistry()

        text = registry.get_prompt_text("create_master_prompts")

        self.assertIsInstance(text, str)
        self.assertTrue(len(text) > 0)

    def test_keys_returns_sorted_prompt_keys(self) -> None:
        registry = MasterPromptRegistry()

        keys = registry.keys()

        self.assertEqual(keys, sorted(keys))
        self.assertTrue(EXPECTED_PROMPT_KEYS.issubset(set(keys)))

    def test_has_returns_true_for_known_key(self) -> None:
        registry = MasterPromptRegistry()

        self.assertTrue(registry.has("create_master_prompts"))
        self.assertFalse(registry.has("this_key_does_not_exist"))

    def test_registry_caches_after_first_load(self) -> None:
        registry = MasterPromptRegistry()
        first = registry.list()
        second = registry.list()

        self.assertIs(registry._cache, registry._cache)
        self.assertEqual([p.key for p in first], [p.key for p in second])

    def test_list_returns_expected_bundled_prompt_keys(self) -> None:
        registry = MasterPromptRegistry()

        keys = {prompt.key for prompt in registry.list()}

        self.assertEqual(keys, EXPECTED_PROMPT_KEYS)


class BundledMasterPromptStructureTests(unittest.TestCase):
    def test_all_bundled_prompts_are_non_empty(self) -> None:
        registry = MasterPromptRegistry()

        for prompt in registry.list():
            with self.subTest(prompt=prompt.key):
                self.assertTrue(prompt.title.strip())
                self.assertTrue(prompt.description.strip())
                self.assertTrue(prompt.prompt.strip())

    def test_all_bundled_prompts_include_core_seven_section_structure(self) -> None:
        registry = MasterPromptRegistry()

        for prompt in registry.list():
            if prompt.key not in STANDARD_STRUCTURE_PROMPT_KEYS:
                continue
            with self.subTest(prompt=prompt.key):
                for section_name in REQUIRED_PROMPT_SECTIONS:
                    _section_position(prompt.prompt, section_name)

    def test_all_bundled_prompts_list_sections_in_order(self) -> None:
        registry = MasterPromptRegistry()

        for prompt in registry.list():
            if prompt.key not in STANDARD_STRUCTURE_PROMPT_KEYS:
                continue
            with self.subTest(prompt=prompt.key):
                positions = [_section_position(prompt.prompt, section_name) for section_name in REQUIRED_PROMPT_SECTIONS]
                self.assertEqual(positions, sorted(positions))

    def test_master_prompt_readme_documents_every_bundled_prompt_title_and_description(self) -> None:
        registry = MasterPromptRegistry()
        readme_text = MASTER_PROMPTS_README.read_text(encoding="utf-8")

        self.assertIn("contains all of our master plans for HarnessIQ", readme_text)

        for prompt in registry.list():
            with self.subTest(prompt=prompt.key):
                self.assertIn(prompt.title, readme_text)
                self.assertIn(prompt.description, readme_text)


class CreateMasterPromptsPromptTests(unittest.TestCase):
    """Verify the bundled create_master_prompts prompt has valid content."""

    def setUp(self) -> None:
        self.prompt = MasterPromptRegistry().get("create_master_prompts")

    def test_title_is_non_empty_string(self) -> None:
        self.assertIsInstance(self.prompt.title, str)
        self.assertTrue(self.prompt.title.strip())

    def test_description_is_non_empty_string(self) -> None:
        self.assertIsInstance(self.prompt.description, str)
        self.assertTrue(self.prompt.description.strip())

    def test_prompt_text_is_non_empty_string(self) -> None:
        self.assertIsInstance(self.prompt.prompt, str)
        self.assertTrue(self.prompt.prompt.strip())

    def test_prompt_text_contains_identity_section_markers(self) -> None:
        text = self.prompt.prompt
        self.assertIn("Identity", text)
        self.assertIn("Goal", text)
        self.assertIn("Checklist", text)

    def test_prompt_key_matches_filename_convention(self) -> None:
        self.assertEqual(self.prompt.key, "create_master_prompts")


class BundledPromptStructureTests(unittest.TestCase):
    def test_all_expected_prompts_are_non_empty(self) -> None:
        registry = MasterPromptRegistry()

        for key in EXPECTED_PROMPT_KEYS:
            with self.subTest(key=key):
                prompt = registry.get(key)
                self.assertTrue(prompt.title.strip())
                self.assertTrue(prompt.description.strip())
                self.assertTrue(prompt.prompt.strip())

    def test_all_expected_prompts_include_core_section_markers(self) -> None:
        registry = MasterPromptRegistry()

        for key in STANDARD_STRUCTURE_PROMPT_KEYS:
            with self.subTest(key=key):
                text = registry.get(key).prompt
                for section_name in REQUIRED_PROMPT_SECTIONS:
                    _section_position(text, section_name)


class MissionDrivenPromptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.prompt = MasterPromptRegistry().get("mission_driven")

    def test_mission_driven_contains_expected_sections(self) -> None:
        for section_name in MISSION_DRIVEN_REQUIRED_SECTIONS:
            with self.subTest(section=section_name):
                _section_position(self.prompt.prompt, section_name)

    def test_mission_driven_sections_appear_in_order(self) -> None:
        positions = [_section_position(self.prompt.prompt, section_name) for section_name in MISSION_DRIVEN_REQUIRED_SECTIONS]
        self.assertEqual(positions, sorted(positions))


class CognitiveMultiplexerPromptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.prompt = MasterPromptRegistry().get("cognitive_multiplexer")

    def test_cognitive_multiplexer_contains_expected_sections(self) -> None:
        for section_name in PERSONA_PROMPT_REQUIRED_SECTIONS:
            with self.subTest(section=section_name):
                _section_position(self.prompt.prompt, section_name)

    def test_cognitive_multiplexer_sections_appear_in_order(self) -> None:
        positions = [_section_position(self.prompt.prompt, section_name) for section_name in PERSONA_PROMPT_REQUIRED_SECTIONS]
        self.assertEqual(positions, sorted(positions))

    def test_cognitive_multiplexer_contains_requested_persona_language(self) -> None:
        self.assertIn("You are a cognitive multiplexer", self.prompt.prompt)
        self.assertIn("You are a cognitive multiplexer \u2014 an expert orchestration system", self.prompt.prompt)
        self.assertIn("You are not trying to produce consensus. You are trying to produce coverage.", self.prompt.prompt)
        self.assertIn("Desired Persona Count (optional):", self.prompt.prompt)

    def test_cognitive_multiplexer_key_matches_filename_convention(self) -> None:
        self.assertEqual(self.prompt.key, "cognitive_multiplexer")


class OrchestratorMasterPromptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.prompt = MasterPromptRegistry().get("orchestrator_master_prompt")

    def test_orchestrator_master_prompt_contains_expected_sections(self) -> None:
        for section_name in PERSONA_PROMPT_REQUIRED_SECTIONS:
            with self.subTest(section=section_name):
                _section_position(self.prompt.prompt, section_name)

    def test_orchestrator_master_prompt_sections_appear_in_order(self) -> None:
        positions = [_section_position(self.prompt.prompt, section_name) for section_name in PERSONA_PROMPT_REQUIRED_SECTIONS]
        self.assertEqual(positions, sorted(positions))

    def test_orchestrator_master_prompt_contains_requested_persona_language(self) -> None:
        self.assertIn("You are a master orchestrator", self.prompt.prompt)
        self.assertIn("You produce graphs, not lists.", self.prompt.prompt)
        self.assertIn("Every agent must be load-bearing.", self.prompt.prompt)
        self.assertIn("Execution Mode (optional).", self.prompt.prompt)

    def test_orchestrator_master_prompt_key_matches_filename_convention(self) -> None:
        self.assertEqual(self.prompt.key, "orchestrator_master_prompt")


class LinkedInJobApplierPromptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.prompt = MasterPromptRegistry().get("linkedin_job_applier")

    def test_linkedin_job_applier_contains_expected_sections(self) -> None:
        for section_name in PERSONA_PROMPT_REQUIRED_SECTIONS:
            with self.subTest(section=section_name):
                _section_position(self.prompt.prompt, section_name)

    def test_linkedin_job_applier_sections_appear_in_order(self) -> None:
        positions = [_section_position(self.prompt.prompt, section_name) for section_name in PERSONA_PROMPT_REQUIRED_SECTIONS]
        self.assertEqual(positions, sorted(positions))

    def test_linkedin_job_applier_contains_requested_persona_language(self) -> None:
        self.assertIn("You are a relentless, methodical job application agent", self.prompt.prompt)
        self.assertIn("You do not apply indiscriminately; you apply precisely.", self.prompt.prompt)
        self.assertIn("You treat the Q&A bank as a first-class input, not a fallback.", self.prompt.prompt)
        self.assertIn("memory/linkedin/applied_jobs.md", self.prompt.prompt)

    def test_linkedin_job_applier_key_matches_filename_convention(self) -> None:
        self.assertEqual(self.prompt.key, "linkedin_job_applier")


class ModuleLevelAPITests(unittest.TestCase):
    def test_get_prompt_returns_master_prompt(self) -> None:
        prompt = get_prompt("create_master_prompts")

        self.assertIsInstance(prompt, MasterPrompt)
        self.assertEqual(prompt.key, "create_master_prompts")

    def test_get_prompt_raises_key_error_for_unknown_key(self) -> None:
        with self.assertRaises(KeyError):
            get_prompt("nonexistent_key_xyz")

    def test_get_prompt_text_returns_raw_string(self) -> None:
        text = get_prompt_text("create_master_prompts")

        self.assertIsInstance(text, str)
        self.assertTrue(len(text) > 0)

    def test_get_prompt_text_matches_get_prompt_dot_prompt(self) -> None:
        self.assertEqual(get_prompt_text("create_master_prompts"), get_prompt("create_master_prompts").prompt)

    def test_list_prompts_returns_list_of_master_prompts(self) -> None:
        prompts = list_prompts()

        self.assertIsInstance(prompts, list)
        self.assertGreaterEqual(len(prompts), len(EXPECTED_PROMPT_KEYS))
        for prompt in prompts:
            self.assertIsInstance(prompt, MasterPrompt)

    def test_list_prompts_returns_expected_bundled_keys(self) -> None:
        prompts = list_prompts()

        self.assertEqual({prompt.key for prompt in prompts}, EXPECTED_PROMPT_KEYS)

    def test_every_expected_prompt_key_is_retrievable_via_public_api(self) -> None:
        for prompt_key in EXPECTED_PROMPT_KEYS:
            with self.subTest(prompt=prompt_key):
                prompt = get_prompt(prompt_key)
                prompt_text = get_prompt_text(prompt_key)

                self.assertEqual(prompt.key, prompt_key)
                self.assertEqual(prompt_text, prompt.prompt)

    def test_list_prompt_keys_returns_sorted_keys(self) -> None:
        keys = list_prompt_keys()

        self.assertEqual(keys, sorted(keys))
        self.assertTrue(EXPECTED_PROMPT_KEYS.issubset(set(keys)))

    def test_has_prompt_reports_presence(self) -> None:
        self.assertTrue(has_prompt("create_master_prompts"))
        self.assertFalse(has_prompt("nonexistent_key_xyz"))

    def test_module_level_api_uses_shared_registry(self) -> None:
        prompt_one = get_prompt("create_master_prompts")
        prompt_two = get_prompt("create_master_prompts")

        self.assertEqual(prompt_one, prompt_two)


class LazyTopLevelImportTests(unittest.TestCase):
    def test_harnessiq_master_prompts_accessible_via_top_level_import(self) -> None:
        import harnessiq

        prompt = harnessiq.master_prompts.get_prompt("create_master_prompts")

        self.assertIsInstance(prompt, MasterPrompt)

    def test_master_prompts_in_harnessiq_dir(self) -> None:
        import harnessiq

        self.assertIn("master_prompts", dir(harnessiq))


if __name__ == "__main__":
    unittest.main()
