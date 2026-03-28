"""Regression coverage for generated repository docs."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

from harnessiq.providers.google_drive import build_google_drive_operation_catalog
from harnessiq.shared.harness_manifests import list_harness_manifests


ROOT = Path(__file__).resolve().parents[1]
SYNC_SCRIPT = ROOT / "scripts" / "sync_repo_docs.py"


def _load_sync_repo_docs_module():
    spec = importlib.util.spec_from_file_location("sync_repo_docs_under_test", SYNC_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load docs sync module from '{SYNC_SCRIPT}'.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DocsSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sync_repo_docs = _load_sync_repo_docs_module()

    def test_generated_docs_are_in_sync(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SYNC_SCRIPT), "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            self.fail(
                "Generated docs are out of sync.\n"
                f"stdout:\n{completed.stdout}\n"
                f"stderr:\n{completed.stderr}"
            )
        self.assertIn("Generated docs are in sync.", completed.stdout)

    def test_expected_outputs_omit_live_inventory_artifact(self) -> None:
        outputs = self.sync_repo_docs.expected_outputs()
        self.assertNotIn(ROOT / "artifacts" / "live_inventory.json", outputs)
        self.assertNotIn("artifacts/live_inventory.json", outputs[ROOT / "README.md"])

    def test_check_outputs_flags_stale_live_inventory_artifact(self) -> None:
        legacy_path = ROOT / "artifacts" / "live_inventory.json"
        legacy_path.write_text("stale\n", encoding="utf-8")
        self.addCleanup(legacy_path.unlink, missing_ok=True)

        drifted = self.sync_repo_docs.check_outputs(self.sync_repo_docs.expected_outputs())

        self.assertIn("artifacts/live_inventory.json", drifted)

    def test_write_outputs_removes_stale_live_inventory_artifact(self) -> None:
        legacy_path = ROOT / "artifacts" / "live_inventory.json"
        legacy_path.write_text("stale\n", encoding="utf-8")
        self.addCleanup(legacy_path.unlink, missing_ok=True)

        self.sync_repo_docs.write_outputs({})

        self.assertFalse(legacy_path.exists())

    def test_inventory_includes_platform_first_cli_roots(self) -> None:
        inventory = self.sync_repo_docs.build_inventory()
        top_level_commands = {entry["command"] for entry in inventory["cli"]["top_level"]}
        self.assertTrue(
            {
                "harnessiq prepare",
                "harnessiq show",
                "harnessiq run",
                "harnessiq inspect",
                "harnessiq credentials",
            }.issubset(top_level_commands)
        )

    def test_inventory_includes_gcloud_command_family(self) -> None:
        inventory = self.sync_repo_docs.build_inventory()
        top_level_commands = {entry["command"] for entry in inventory["cli"]["top_level"]}
        self.assertIn("harnessiq gcloud", top_level_commands)

    def test_inventory_matches_live_harness_manifests(self) -> None:
        inventory = self.sync_repo_docs.build_inventory()
        inventory_harnesses = {entry["manifest_id"]: entry for entry in inventory["harnesses"]}
        runtime_harnesses = {manifest.manifest_id: manifest for manifest in list_harness_manifests()}

        self.assertEqual(set(inventory_harnesses), set(runtime_harnesses))

        for manifest_id, manifest in runtime_harnesses.items():
            entry = inventory_harnesses[manifest_id]
            self.assertEqual(entry["display_name"], manifest.display_name)
            self.assertEqual(entry["module_path"], manifest.module_path)
            self.assertEqual(entry["class_name"], manifest.class_name)
            self.assertEqual(entry["cli_command"], manifest.cli_command)
            self.assertEqual(entry["default_memory_root"], manifest.resolved_default_memory_root)
            self.assertEqual(
                [item["key"] for item in entry["runtime_parameters"]],
                list(manifest.runtime_parameter_names),
            )
            self.assertEqual(
                [item["key"] for item in entry["custom_parameters"]],
                list(manifest.custom_parameter_names),
            )
            self.assertEqual(
                [item["relative_path"] for item in entry["memory_files"]],
                [item.relative_path for item in manifest.memory_files],
            )
            self.assertEqual(entry["provider_families"], list(manifest.provider_families))
            self.assertEqual(
                entry["output_fields"],
                sorted(manifest.output_schema.get("properties", {})),
            )

    def test_inventory_includes_focused_subpackage_context(self) -> None:
        inventory = self.sync_repo_docs.build_inventory()
        focused_subpackages = {
            entry["path"]: entry["description"] for entry in inventory["focused_subpackages"]
        }
        self.assertIn("harnessiq/cli/adapters/", focused_subpackages)
        self.assertIn("harnessiq/cli/adapters/utils/", focused_subpackages)
        self.assertIn("harnessiq/config/provider_credentials/", focused_subpackages)
        self.assertIn("harnessiq/utils/harness_manifest/", focused_subpackages)

    def test_top_level_directory_classifier_preserves_exact_match_metadata(self) -> None:
        classified = self.sync_repo_docs.classify_top_level_directory(ROOT / "artifacts")
        self.assertEqual(classified["kind"], "repo docs")
        self.assertEqual(
            classified["description"],
            "Generated and curated repository reference artifacts.",
        )

    def test_top_level_directory_classifier_handles_local_state_overrides(self) -> None:
        worktrees = self.sync_repo_docs.classify_top_level_directory(ROOT / ".worktrees")
        self.assertEqual(worktrees["kind"], "local state")
        self.assertIn("Git worktree checkouts", worktrees["description"])

        data = self.sync_repo_docs.classify_top_level_directory(ROOT / "data")
        self.assertEqual(data["kind"], "local state")
        self.assertIn("Local datasets, exports, and scratch runtime artifacts", data["description"])

    def test_top_level_directory_classifier_uses_generic_fallback_for_unknown_names(self) -> None:
        classified = self.sync_repo_docs.classify_top_level_directory(ROOT / "unclassified-root")
        self.assertEqual(classified["kind"], "other")
        self.assertEqual(
            classified["description"],
            "Repository directory not yet classified in the generated file index.",
        )

    def test_google_drive_operation_count_matches_live_catalog(self) -> None:
        inventory = self.sync_repo_docs.build_inventory()
        provider_index = {
            provider["family"]: provider for provider in inventory["providers"]["service_providers"]
        }
        self.assertEqual(
            provider_index["google_drive"]["operations"],
            len(build_google_drive_operation_catalog()),
        )


if __name__ == "__main__":
    unittest.main()
