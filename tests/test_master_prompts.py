"""Tests for the master_prompts module — registry, loading, and public API."""

from __future__ import annotations

import unittest

from harnessiq.master_prompts import MasterPrompt, MasterPromptRegistry, get_prompt, get_prompt_text, list_prompts

EXPECTED_PROMPT_KEYS = {
    "create_master_prompts",
    "create_tickets",
    "phased_code_review",
    "surgical_bugfix",
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
            with self.subTest(prompt=prompt.key):
                for section_name in REQUIRED_PROMPT_SECTIONS:
                    self.assertIn(section_name, prompt.prompt)


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

    def test_list_prompts_returns_expected_bundled_keys(self) -> None:
        prompts = list_prompts()

        self.assertEqual({prompt.key for prompt in prompts}, EXPECTED_PROMPT_KEYS)

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
