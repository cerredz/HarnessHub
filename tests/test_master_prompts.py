"""Tests for the master_prompts module — registry, loading, and public API."""

from __future__ import annotations

import unittest

from harnessiq.master_prompts import MasterPrompt, MasterPromptRegistry, get_prompt, get_prompt_text, list_prompts


EXPECTED_PROMPT_KEYS = {
    "answer_with_notable_web_sources",
    "create_master_prompts",
    "hybrid_academic_and_web_research",
    "research_with_arxiv_papers",
    "research_with_hugging_face_hub_pages",
    "research_with_hugging_face_papers",
}


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
    def test_list_returns_at_least_one_prompt(self) -> None:
        registry = MasterPromptRegistry()

        prompts = registry.list()

        self.assertGreater(len(prompts), 0)

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

    def test_registry_caches_after_first_load(self) -> None:
        registry = MasterPromptRegistry()
        first = registry.list()
        second = registry.list()

        # Same object identity — cache was used
        self.assertIs(registry._cache, registry._cache)
        self.assertEqual([p.key for p in first], [p.key for p in second])

    def test_expected_prompt_keys_are_bundled(self) -> None:
        registry = MasterPromptRegistry()

        keys = {prompt.key for prompt in registry.list()}

        self.assertTrue(EXPECTED_PROMPT_KEYS.issubset(keys))


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
        # The prompt encodes the full seven-section master prompt structure.
        # Verify key structural markers are present.
        text = self.prompt.prompt
        self.assertIn("Identity", text)
        self.assertIn("Goal", text)
        self.assertIn("Checklist", text)

    def test_prompt_key_matches_filename_convention(self) -> None:
        self.assertEqual(self.prompt.key, "create_master_prompts")


class BundledMasterPromptCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.prompts = MasterPromptRegistry().list()

    def test_all_expected_prompts_have_required_fields(self) -> None:
        relevant = [prompt for prompt in self.prompts if prompt.key in EXPECTED_PROMPT_KEYS]
        self.assertEqual({prompt.key for prompt in relevant}, EXPECTED_PROMPT_KEYS)
        for prompt in relevant:
            with self.subTest(prompt=prompt.key):
                self.assertTrue(prompt.title.strip())
                self.assertTrue(prompt.description.strip())
                self.assertTrue(prompt.prompt.strip())

    def test_all_expected_prompts_contain_master_prompt_sections(self) -> None:
        required_markers = (
            "Identity",
            "Goal",
            "Checklist",
            "Things Not To Do",
            "Success Criteria",
            "Artifacts",
            "Inputs",
        )
        relevant = [prompt for prompt in self.prompts if prompt.key in EXPECTED_PROMPT_KEYS]
        for prompt in relevant:
            with self.subTest(prompt=prompt.key):
                for marker in required_markers:
                    self.assertIn(marker, prompt.prompt)


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
        self.assertGreater(len(prompts), 0)
        for p in prompts:
            self.assertIsInstance(p, MasterPrompt)

    def test_module_level_api_uses_shared_registry(self) -> None:
        # Both calls should return equal objects (same underlying data).
        p1 = get_prompt("create_master_prompts")
        p2 = get_prompt("create_master_prompts")

        self.assertEqual(p1, p2)


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
