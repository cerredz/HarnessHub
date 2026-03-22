"""Tests for the shared agent-instance registry utilities."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harnessiq.utils import (
    AgentInstanceStore,
    build_agent_instance_id,
    build_default_instance_name,
    fingerprint_agent_payload,
)


class AgentInstanceStoreTests(unittest.TestCase):
    def test_helpers_are_stable_for_equal_payloads(self) -> None:
        payload = {"config": {"max_tokens": 1000}, "tags": ["a", "b"]}

        first_fingerprint = fingerprint_agent_payload(payload)
        second_fingerprint = fingerprint_agent_payload({"tags": ["a", "b"], "config": {"max_tokens": 1000}})
        first_id = build_agent_instance_id("linkedin_job_applier", payload)
        second_id = build_agent_instance_id("linkedin_job_applier", {"tags": ["a", "b"], "config": {"max_tokens": 1000}})

        self.assertEqual(first_fingerprint, second_fingerprint)
        self.assertEqual(first_id, second_id)
        self.assertEqual(
            build_default_instance_name("linkedin_job_applier", payload),
            build_default_instance_name("linkedin_job_applier", payload),
        )

    def test_store_resolves_same_payload_to_same_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = AgentInstanceStore(repo_root=temp_dir)
            payload = {"query": "staff platform", "save_to_google_drive": False}

            first = store.resolve(agent_name="linkedin_job_applier", payload=payload)
            second = store.resolve(agent_name="linkedin_job_applier", payload=dict(payload))

            self.assertEqual(first.instance_id, second.instance_id)
            self.assertEqual(first.memory_path, second.memory_path)
            self.assertEqual(len(store.list_instances(agent_name="linkedin_job_applier")), 1)
            self.assertTrue((Path(temp_dir) / "memory" / "agent_instances.json").exists())

    def test_store_creates_distinct_records_for_different_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = AgentInstanceStore(repo_root=temp_dir)

            first = store.resolve(agent_name="linkedin_job_applier", payload={"query": "staff platform"})
            second = store.resolve(agent_name="linkedin_job_applier", payload={"query": "principal ml"})

            self.assertNotEqual(first.instance_id, second.instance_id)
            self.assertEqual(len(store.list_instances(agent_name="linkedin_job_applier")), 2)

    def test_store_uses_explicit_memory_path_and_instance_name_when_provided(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = AgentInstanceStore(repo_root=temp_dir)
            explicit_memory_path = Path(temp_dir) / "memory" / "linkedin" / "candidate-a"

            record = store.resolve(
                agent_name="linkedin_job_applier",
                payload={"query": "staff platform"},
                instance_name="candidate-a",
                memory_path=explicit_memory_path,
            )

            self.assertEqual(record.instance_name, "candidate-a")
            self.assertEqual(record.memory_path, explicit_memory_path)
            reloaded = store.get(record.instance_id)
            self.assertEqual(reloaded.memory_path, explicit_memory_path)


if __name__ == "__main__":
    unittest.main()
