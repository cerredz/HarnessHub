from __future__ import annotations

import json
from pathlib import Path

from harnessiq.config import (
    HarnessProfile,
    HarnessProfileIndexStore,
    HarnessProfileStore,
    HarnessRunSnapshot,
)


def test_harness_profile_from_dict_remains_backward_compatible() -> None:
    profile = HarnessProfile.from_dict(
        {
            "agent_name": "creator-a",
            "custom_parameters": {"segment": "fitness"},
            "manifest_id": "instagram",
            "runtime_parameters": {"max_tokens": 4096},
        }
    )

    assert profile.manifest_id == "instagram"
    assert profile.agent_name == "creator-a"
    assert profile.last_run is None
    assert profile.run_history == ()


def test_harness_profile_store_persists_last_run_snapshot(tmp_path: Path) -> None:
    store = HarnessProfileStore(tmp_path / "creator-a")
    profile = HarnessProfile(
        manifest_id="instagram",
        agent_name="creator-a",
        runtime_parameters={"max_tokens": 4096},
        custom_parameters={"segment": "fitness"},
        last_run=HarnessRunSnapshot(
            model_factory="tests.test_platform_cli:create_static_model",
            sink_specs=("jsonl:data/runs.jsonl",),
            max_cycles=12,
            adapter_arguments={"search_backend_factory": "tests.test_platform_cli:create_special_instagram_search_backend"},
            runtime_parameters={"max_tokens": 4096},
            custom_parameters={"segment": "fitness"},
            recorded_at="2026-03-24T00:00:00Z",
        ),
    )

    store.save(profile)
    reloaded = store.load(manifest_id="instagram", agent_name="creator-a")

    assert reloaded.last_run is not None
    assert reloaded.last_run.run_number == 1
    assert reloaded.last_run.model_factory == "tests.test_platform_cli:create_static_model"
    assert reloaded.last_run.sink_specs == ("jsonl:data/runs.jsonl",)
    assert reloaded.last_run.adapter_arguments["search_backend_factory"].endswith(
        "create_special_instagram_search_backend"
    )
    assert reloaded.last_run.runtime_parameters == {"max_tokens": 4096}
    assert reloaded.last_run.custom_parameters == {"segment": "fitness"}
    assert len(reloaded.run_history) == 1


def test_harness_profile_from_legacy_last_run_populates_run_history() -> None:
    profile = HarnessProfile.from_dict(
        {
            "agent_name": "creator-a",
            "custom_parameters": {"segment": "fitness"},
            "last_run": {
                "adapter_arguments": {
                    "search_backend_factory": "tests.test_platform_cli:create_special_instagram_search_backend"
                },
                "custom_parameters": {"segment": "fitness"},
                "max_cycles": 12,
                "model_factory": "tests.test_platform_cli:create_static_model",
                "recorded_at": "2026-03-24T00:00:00Z",
                "runtime_parameters": {"max_tokens": 4096},
                "sink_specs": ["jsonl:data/runs.jsonl"],
            },
            "manifest_id": "instagram",
            "runtime_parameters": {"max_tokens": 4096},
        }
    )

    assert profile.last_run is not None
    assert profile.last_run.run_number == 1
    assert profile.last_run.runtime_parameters == {"max_tokens": 4096}
    assert profile.last_run.custom_parameters == {"segment": "fitness"}
    assert len(profile.run_history) == 1
    assert profile.run_history[0].run_number == 1
    assert profile.snapshot_for_run_number(1) == profile.last_run


def test_harness_profile_append_run_snapshot_assigns_next_run_number() -> None:
    profile = HarnessProfile(
        manifest_id="instagram",
        agent_name="creator-a",
        runtime_parameters={"max_tokens": 4096},
        custom_parameters={"segment": "fitness"},
    ).append_run_snapshot(
        HarnessRunSnapshot(
            model_factory="tests.test_platform_cli:create_static_model",
            sink_specs=("jsonl:data/runs.jsonl",),
            max_cycles=12,
            adapter_arguments={"search_backend_factory": "tests.test_platform_cli:create_special_instagram_search_backend"},
            runtime_parameters={"max_tokens": 4096},
            custom_parameters={"segment": "fitness"},
            recorded_at="2026-03-24T00:00:00Z",
        )
    ).append_run_snapshot(
        HarnessRunSnapshot(
            model_factory="tests.test_platform_cli:create_static_model",
            sink_specs=("jsonl:data/runs-2.jsonl",),
            max_cycles=24,
            adapter_arguments={"search_backend_factory": "tests.test_platform_cli:create_instagram_search_backend"},
            runtime_parameters={"max_tokens": 8192},
            custom_parameters={"segment": "education"},
            recorded_at="2026-03-24T01:00:00Z",
        )
    )

    assert [snapshot.run_number for snapshot in profile.run_history] == [1, 2]
    assert profile.last_run == profile.run_history[-1]
    assert profile.snapshot_for_run_number(2) == profile.last_run


def test_harness_profile_index_store_round_trips_paths(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    memory_path = repo_root / "memory" / "instagram" / "creator-a"
    index_store = HarnessProfileIndexStore(repo_root=repo_root)

    record = index_store.upsert(
        manifest_id="instagram",
        agent_name="creator-a",
        memory_path=memory_path,
        updated_at="2026-03-24T00:00:00Z",
    )

    assert record.memory_path == memory_path
    reloaded = index_store.list(agent_name="creator-a", manifest_id="instagram")
    assert len(reloaded) == 1
    assert reloaded[0].memory_path == memory_path

    payload = json.loads(index_store.index_path.read_text(encoding="utf-8"))
    assert payload["records"][0]["memory_path"] == "memory/instagram/creator-a"
