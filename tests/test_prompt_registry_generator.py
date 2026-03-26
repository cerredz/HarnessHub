"""Tests for the prompt registry generator script."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from datetime import datetime
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "generate_prompt_registry.py"
PROMPTS_DIR = ROOT / "artifacts" / "prompts"
REGISTRY_PATH = PROMPTS_DIR / "registry.json"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("generate_prompt_registry_under_test", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load prompt registry generator from '{SCRIPT_PATH}'.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class PromptRegistryGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.generator = _load_script_module()

    def test_generated_registry_is_in_sync(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            self.fail(
                "Prompt registry is out of sync.\n"
                f"stdout:\n{completed.stdout}\n"
                f"stderr:\n{completed.stderr}"
            )
        self.assertIn("Prompt registry is in sync.", completed.stdout)

    def test_build_registry_matches_prompt_markdown_files(self) -> None:
        payload = self.generator.build_registry()

        prompt_files = sorted(path.stem for path in PROMPTS_DIR.glob("*.md"))
        registry_names = [item["name"] for item in payload["harnesses"]]

        self.assertEqual(registry_names, prompt_files)

    def test_registry_entries_include_required_fields(self) -> None:
        payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))

        for entry in payload["harnesses"]:
            with self.subTest(prompt=entry["name"]):
                self.assertTrue(entry["name"])
                self.assertTrue(entry["description"])
                self.assertTrue(entry["updated_at"])
                datetime.fromisoformat(entry["updated_at"].replace("Z", "+00:00"))

    def test_description_derivation_skips_heading_only_blocks(self) -> None:
        prompt_text = "\n\n".join(
            [
                "Identity",
                "You are a world-class debugging specialist.",
                "Goal",
            ]
        )
        description = self.generator._derive_description(prompt_text)
        self.assertEqual(description, "You are a world-class debugging specialist.")

    def test_build_registry_supports_non_repo_temp_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            prompts_dir = Path(temp_dir)
            (prompts_dir / "example.md").write_text("You are a reliable agent.\n", encoding="utf-8")

            payload = self.generator.build_registry(prompts_dir=prompts_dir)

        self.assertEqual(payload["harnesses"][0]["name"], "example")
        self.assertEqual(payload["harnesses"][0]["description"], "You are a reliable agent.")

    def test_write_registry_writes_rendered_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            prompts_dir = temp_root / "prompts"
            prompts_dir.mkdir()
            (prompts_dir / "example.md").write_text("You are a reliable agent.\n", encoding="utf-8")
            registry_path = temp_root / "registry.json"

            written = self.generator.write_registry(prompts_dir=prompts_dir, registry_path=registry_path)

            self.assertEqual(written, self.generator.render_registry(prompts_dir=prompts_dir))
            self.assertEqual(registry_path.read_text(encoding="utf-8"), written)


if __name__ == "__main__":
    unittest.main()
