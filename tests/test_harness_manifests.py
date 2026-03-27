"""Tests for the shared harness manifest registry and coercion helpers."""

from __future__ import annotations

import unittest

from harnessiq.cli.common import parse_manifest_parameter_assignments
from harnessiq.shared import HARNESS_MANIFESTS, get_harness_manifest
from harnessiq.shared.exa_outreach import EXA_OUTREACH_HARNESS_MANIFEST
from harnessiq.shared.instagram import INSTAGRAM_HARNESS_MANIFEST
from harnessiq.shared.leads import LEADS_HARNESS_MANIFEST
from harnessiq.shared.linkedin import LINKEDIN_HARNESS_MANIFEST
from harnessiq.shared.mission_driven import MISSION_DRIVEN_HARNESS_MANIFEST
from harnessiq.shared.research_sweep import RESEARCH_SWEEP_HARNESS_MANIFEST
from harnessiq.shared.spawn_specialized_subagents import SPAWN_SPECIALIZED_SUBAGENTS_HARNESS_MANIFEST


class HarnessManifestRegistryTests(unittest.TestCase):
    def test_registry_resolves_by_manifest_id_agent_name_and_cli_command(self) -> None:
        self.assertIs(get_harness_manifest("linkedin"), LINKEDIN_HARNESS_MANIFEST)
        self.assertIs(get_harness_manifest("linkedin_job_applier"), LINKEDIN_HARNESS_MANIFEST)
        self.assertIs(get_harness_manifest("mission_driven"), MISSION_DRIVEN_HARNESS_MANIFEST)
        self.assertIs(get_harness_manifest("outreach"), EXA_OUTREACH_HARNESS_MANIFEST)
        self.assertIs(get_harness_manifest("research-sweep"), RESEARCH_SWEEP_HARNESS_MANIFEST)
        self.assertIs(
            get_harness_manifest("spawn_specialized_subagents"),
            SPAWN_SPECIALIZED_SUBAGENTS_HARNESS_MANIFEST,
        )

    def test_registry_contains_all_built_in_manifests(self) -> None:
        self.assertEqual(
            set(HARNESS_MANIFESTS),
            {
                "exa_outreach",
                "instagram",
                "knowt",
                "leads",
                "linkedin",
                "mission_driven",
                "prospecting",
                "research_sweep",
                "spawn_specialized_subagents",
            },
        )
        for manifest in HARNESS_MANIFESTS.values():
            self.assertTrue(manifest.memory_files)
            self.assertTrue(manifest.display_name)
            self.assertTrue(manifest.import_path)


class HarnessManifestCoercionTests(unittest.TestCase):
    def test_linkedin_manifest_allows_open_ended_custom_parameters(self) -> None:
        payload = LINKEDIN_HARNESS_MANIFEST.coerce_custom_parameters(
            {"target_level": "staff", "remote_only": True}
        )
        self.assertEqual(payload["target_level"], "staff")
        self.assertTrue(payload["remote_only"])

    def test_instagram_manifest_allows_open_ended_custom_parameters(self) -> None:
        payload = INSTAGRAM_HARNESS_MANIFEST.coerce_custom_parameters(
            {"icp_profiles": ["fitness creators"], "research_mode": True}
        )
        self.assertEqual(payload["icp_profiles"], ["fitness creators"])
        self.assertTrue(payload["research_mode"])

    def test_leads_manifest_coerces_nullable_runtime_parameters(self) -> None:
        payload = LEADS_HARNESS_MANIFEST.coerce_runtime_parameters(
            {
                "max_tokens": "4096",
                "reset_threshold": "0.8",
                "prune_search_interval": "",
                "max_leads_per_icp": None,
            }
        )
        self.assertEqual(payload["max_tokens"], 4096)
        self.assertEqual(payload["reset_threshold"], 0.8)
        self.assertIsNone(payload["prune_search_interval"])
        self.assertIsNone(payload["max_leads_per_icp"])

    def test_cli_assignment_helper_uses_manifest_rules(self) -> None:
        payload = parse_manifest_parameter_assignments(
            ["max_tokens=60000", "reset_threshold=0.75"],
            manifest=EXA_OUTREACH_HARNESS_MANIFEST,
            scope="runtime",
        )
        self.assertEqual(payload, {"max_tokens": 60000, "reset_threshold": 0.75})


if __name__ == "__main__":
    unittest.main()
