from __future__ import annotations

import json
from pathlib import Path

import pytest

from harnessiq.config import HarnessProfile, HarnessProfileIndexStore, HarnessProfileStore, HarnessRunSnapshot
from harnessiq.providers.gcloud import GcpAgentConfig, GcpContext, GcloudClient, derive_deploy_spec
from harnessiq.providers.gcloud.manifest_support import (
    ENV_ADAPTER_ARGUMENTS,
    ENV_AGENT_NAME,
    ENV_CUSTOM_PARAMETERS,
    ENV_MANIFEST_ID,
    ENV_MAX_CYCLES,
    ENV_MEMORY_FILES,
    ENV_MEMORY_PATH,
    ENV_MODEL_SELECTION,
    ENV_PROVIDER_FAMILIES,
    ENV_RUNTIME_PARAMETERS,
    ENV_SINK_SPECS,
    RUNTIME_MODULE,
)
from harnessiq.shared import HARNESS_MANIFESTS
from harnessiq.shared.harness_manifest import HarnessParameterSpec


def test_derive_deploy_spec_supports_every_builtin_manifest(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    for manifest in HARNESS_MANIFESTS.values():
        config = GcpAgentConfig(
            agent_name=f"{manifest.manifest_id}-runner",
            gcp_project_id="proj-123",
            region="us-central1",
            manifest_id=manifest.manifest_id,
            memory_path=f"memory/cloud/{manifest.manifest_id}/runner",
            model="openai:gpt-5.4",
            runtime_parameters=_required_parameters(manifest.runtime_parameters),
            custom_parameters=_required_parameters(manifest.custom_parameters),
        )

        spec = derive_deploy_spec(config, repo_root=repo_root)

        assert spec.manifest_id == manifest.manifest_id
        assert spec.display_name == manifest.display_name
        assert spec.memory_path == f"memory/cloud/{manifest.manifest_id}/runner"
        assert spec.model_selection.as_dict() == {"model": "openai:gpt-5.4"}
        assert spec.remote_command[:3] == ("python", "-m", RUNTIME_MODULE)
        assert spec.remote_command[3:] == (
            "--manifest-id",
            manifest.manifest_id,
            "--agent",
            config.agent_name,
            "--memory-path",
            spec.memory_path,
        )
        assert json.loads(spec.env_vars[ENV_PROVIDER_FAMILIES]) == list(manifest.provider_families)
        assert json.loads(spec.env_vars[ENV_MEMORY_FILES]) == [entry.as_dict() for entry in spec.memory_entries]


def test_derive_deploy_spec_merges_profile_state_for_research_sweep(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    memory_path = repo_root / "memory" / "research_sweep" / "candidate-a"
    HarnessProfileStore(memory_path).save(
        HarnessProfile(
            manifest_id="research_sweep",
            agent_name="candidate-a",
            runtime_parameters={"max_tokens": 48000, "reset_threshold": 0.7},
            custom_parameters={"query": "profile query", "allowed_serper_operations": "search,scholar"},
            last_run=HarnessRunSnapshot(
                model_profile="anthropic-default",
                sink_specs=("jsonl:data/profile.jsonl",),
                max_cycles=17,
                adapter_arguments={"search_backend_factory": "tests.factories:create_backend"},
                runtime_parameters={"max_tokens": 48000, "reset_threshold": 0.7},
                custom_parameters={"query": "profile query", "allowed_serper_operations": "search,scholar"},
                recorded_at="2026-03-24T00:00:00Z",
            ),
        )
    )
    HarnessProfileIndexStore(repo_root=repo_root).upsert(
        manifest_id="research_sweep",
        agent_name="candidate-a",
        memory_path=memory_path,
        updated_at="2026-03-24T00:00:00Z",
    )

    config = GcpAgentConfig(
        agent_name="candidate-a",
        gcp_project_id="proj-123",
        region="us-central1",
        manifest_id="research_sweep",
        model="openai:gpt-5.4",
        max_cycles=9,
        sink_specs=["jsonl:data/override.jsonl"],
        adapter_arguments={"dry_run": True},
        runtime_parameters={"reset_threshold": 0.92},
        custom_parameters={"query": "AI chip export controls"},
        env_vars={"EXISTING_ENV": "1"},
        secrets=[{"env_var": "ANTHROPIC_API_KEY", "secret_name": "HARNESSIQ_ANTHROPIC_API_KEY"}],
    )

    spec = derive_deploy_spec(config, repo_root=repo_root)

    assert spec.memory_path == "memory/research_sweep/candidate-a"
    assert spec.model_selection.as_dict() == {"model": "openai:gpt-5.4"}
    assert spec.max_cycles == 9
    assert spec.sink_specs == ("jsonl:data/override.jsonl",)
    assert spec.adapter_arguments == {
        "dry_run": True,
        "search_backend_factory": "tests.factories:create_backend",
    }
    assert spec.runtime_parameters == {"max_tokens": 48000, "reset_threshold": 0.92}
    assert spec.custom_parameters == {
        "allowed_serper_operations": "search,scholar",
        "query": "AI chip export controls",
    }
    assert spec.secret_references[0].as_dict() == {
        "env_var": "ANTHROPIC_API_KEY",
        "secret_name": "HARNESSIQ_ANTHROPIC_API_KEY",
    }
    assert spec.remote_command == (
        "python",
        "-m",
        RUNTIME_MODULE,
        "--manifest-id",
        "research_sweep",
        "--agent",
        "candidate-a",
        "--memory-path",
        "memory/research_sweep/candidate-a",
    )

    assert spec.env_vars["EXISTING_ENV"] == "1"
    assert spec.env_vars[ENV_MANIFEST_ID] == "research_sweep"
    assert spec.env_vars[ENV_AGENT_NAME] == "candidate-a"
    assert spec.env_vars[ENV_MEMORY_PATH] == "memory/research_sweep/candidate-a"
    assert spec.env_vars[ENV_MAX_CYCLES] == "9"
    assert json.loads(spec.env_vars[ENV_MODEL_SELECTION]) == {"model": "openai:gpt-5.4"}
    assert json.loads(spec.env_vars[ENV_RUNTIME_PARAMETERS]) == spec.runtime_parameters
    assert json.loads(spec.env_vars[ENV_CUSTOM_PARAMETERS]) == spec.custom_parameters
    assert json.loads(spec.env_vars[ENV_ADAPTER_ARGUMENTS]) == spec.adapter_arguments
    assert json.loads(spec.env_vars[ENV_SINK_SPECS]) == ["jsonl:data/override.jsonl"]


def test_context_derive_deploy_spec_prefers_explicit_memory_path(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    explicit_memory_path = repo_root / "custom-memory" / "instagram" / "creator-a"
    HarnessProfileStore(explicit_memory_path).save(
        HarnessProfile(
            manifest_id="instagram",
            agent_name="creator-a",
            runtime_parameters={"search_result_limit": 12},
            custom_parameters={"icp_profiles": ["fitness creators"]},
            last_run=HarnessRunSnapshot(
                model_factory="tests.factories:create_model",
                sink_specs=("jsonl:data/profile.jsonl",),
                max_cycles=6,
                adapter_arguments={"search_backend_factory": "tests.factories:create_instagram_backend"},
                runtime_parameters={"search_result_limit": 12},
                custom_parameters={"icp_profiles": ["fitness creators"]},
                recorded_at="2026-03-24T00:00:00Z",
            ),
        )
    )
    HarnessProfileIndexStore(repo_root=repo_root).upsert(
        manifest_id="instagram",
        agent_name="creator-a",
        memory_path=repo_root / "memory" / "instagram" / "ignored-index-record",
        updated_at="2026-03-24T00:00:00Z",
    )
    context = GcpContext(
        GcloudClient(project_id="proj-123", region="us-central1", dry_run=True),
        GcpAgentConfig(
            agent_name="creator-a",
            gcp_project_id="proj-123",
            region="us-central1",
            manifest_id="instagram",
            memory_path="custom-memory/instagram/creator-a",
            model_profile="ops-fast",
            runtime_parameters={"recent_result_window": 6},
            custom_parameters={"icp_profiles": ["founders"]},
            adapter_arguments={"timeout_ms": 30000},
        ),
    )

    spec = context.derive_deploy_spec(repo_root=repo_root)

    assert spec.memory_path == "custom-memory/instagram/creator-a"
    assert spec.model_selection.as_dict() == {"model_profile": "ops-fast"}
    assert spec.provider_families == ("playwright",)
    assert {entry.key for entry in spec.memory_entries} >= {"icp_profiles", "lead_database", "run_state"}
    assert spec.runtime_parameters["search_result_limit"] == 12
    assert spec.runtime_parameters["recent_result_window"] == 6
    assert spec.custom_parameters == {"icp_profiles": ["founders"]}
    assert spec.adapter_arguments == {
        "search_backend_factory": "tests.factories:create_instagram_backend",
        "timeout_ms": 30000,
    }


def test_derive_deploy_spec_requires_model_selection_when_snapshot_missing(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    config = GcpAgentConfig(
        agent_name="candidate-a",
        gcp_project_id="proj-123",
        region="us-central1",
        manifest_id="research_sweep",
        memory_path="memory/research_sweep/candidate-a",
        custom_parameters={"query": "AI chip export controls"},
    )

    with pytest.raises(ValueError, match="model selection"):
        derive_deploy_spec(config, repo_root=repo_root)


def _required_parameters(specs: tuple[HarnessParameterSpec, ...]) -> dict[str, object]:
    return {
        spec.key: _sample_parameter_value(spec)
        for spec in specs
        if spec.default is None
    }


def _sample_parameter_value(spec: HarnessParameterSpec) -> object:
    if spec.choices:
        return spec.choices[0]
    if spec.value_type == "integer":
        return 7
    if spec.value_type == "number":
        return 0.75
    if spec.value_type == "boolean":
        return True
    return f"sample-{spec.key}"
