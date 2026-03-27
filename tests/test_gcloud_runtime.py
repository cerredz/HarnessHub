from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
from contextlib import redirect_stdout

import pytest

from harnessiq.cli.adapters import HarnessAdapterContext
from harnessiq.config import HarnessProfile
from harnessiq.providers.gcloud import GcpAgentConfig
from harnessiq.providers.gcloud.runtime import main, run_runtime
from harnessiq.providers.gcloud.storage import CloudStorageProvider
from harnessiq.shared.harness_manifest import HarnessManifest
from harnessiq.providers.gcloud.manifest_support import GcpDeploySpec, GcpMemoryEntry, GcpModelSelection


class _RecordingClient:
    def __init__(self, responses: dict[tuple[str, ...], str] | None = None) -> None:
        self.responses = responses or {}
        self.commands: list[tuple[str, ...]] = []

    def run(self, args: list[str]) -> str:
        command = tuple(args)
        self.commands.append(command)
        return self.responses.get(command, "")


class _RecordingStorage:
    def __init__(self, *, synced_from_gcs: bool = True) -> None:
        self.synced_from_gcs = synced_from_gcs
        self.actions: list[tuple[str, str, str]] = []

    def runtime_state_uri(self, memory_path: str) -> str:
        return f"gs://bucket/runtime-state/{memory_path}/"

    def sync_memory_from_gcs(self, memory_path: str, local_path: Path | str) -> bool:
        self.actions.append(("download", memory_path, str(local_path)))
        Path(local_path).mkdir(parents=True, exist_ok=True)
        return self.synced_from_gcs

    def sync_memory_to_gcs(self, memory_path: str, local_path: Path | str) -> bool:
        self.actions.append(("upload", memory_path, str(local_path)))
        return True


class _FakeAdapter:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.seen_args: argparse.Namespace | None = None

    def register_run_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--search-backend-factory", default="default.factory")

    def run(self, *, args, context, model, runtime_config):
        self.seen_args = args
        assert model == "resolved-model"
        assert runtime_config == {"sink_specs": ("jsonl:data/cloud.jsonl",)}
        if self.should_fail:
            raise RuntimeError("adapter boom")
        return {
            "adapter_result": "ok",
            "memory_path_seen": str(context.memory_path),
        }


class _FakeGcpContext:
    def __init__(self, *, config: GcpAgentConfig, storage: _RecordingStorage, deploy_spec: GcpDeploySpec) -> None:
        self.config = config
        self.storage = storage
        self._deploy_spec = deploy_spec

    def derive_deploy_spec(self, *, repo_root: Path | str = ".") -> GcpDeploySpec:
        del repo_root
        return self._deploy_spec


def test_cloud_storage_provider_sync_helpers_use_runtime_state_prefix(tmp_path: Path) -> None:
    local_path = tmp_path / "memory" / "research_sweep" / "candidate-a"
    local_path.mkdir(parents=True)
    client = _RecordingClient(
        responses={
            ("storage", "ls", "gs://harnessiq-proj-123-agent-memory/runtime-state/memory/research_sweep/candidate-a/"): "",
        }
    )
    provider = CloudStorageProvider(
        client=client,
        config=GcpAgentConfig(
            agent_name="candidate-a",
            gcp_project_id="proj-123",
            region="us-central1",
        ),
    )

    assert (
        provider.runtime_state_uri("memory/research_sweep/candidate-a")
        == "gs://harnessiq-proj-123-agent-memory/runtime-state/memory/research_sweep/candidate-a/"
    )
    assert provider.sync_memory_from_gcs("memory/research_sweep/candidate-a", local_path) is False
    assert provider.sync_memory_to_gcs("memory/research_sweep/candidate-a", local_path) is True
    assert client.commands[-1] == (
        "storage",
        "rsync",
        str(local_path),
        "gs://harnessiq-proj-123-agent-memory/runtime-state/memory/research_sweep/candidate-a/",
        "--recursive",
        "--delete-unmatched-destination-objects",
    )


def test_run_runtime_syncs_state_and_executes_generic_adapter(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    memory_path = "memory/research_sweep/candidate-a"
    local_memory_path = tmp_path / "repo" / "memory" / "research_sweep" / "candidate-a"
    storage = _RecordingStorage()
    adapter = _FakeAdapter()
    manifest = HarnessManifest(
        manifest_id="research_sweep",
        agent_name="research_sweep_agent",
        display_name="Research Sweep",
        module_path="tests.fake",
        class_name="FakeAgent",
    )
    deploy_spec = GcpDeploySpec(
        manifest_id="research_sweep",
        display_name="Research Sweep",
        agent_name="candidate-a",
        memory_path=memory_path,
        provider_families=(),
        memory_entries=(GcpMemoryEntry(key="query", relative_path="query.txt", kind="file", format="text", description="Query"),),
        model_selection=GcpModelSelection(model="openai:gpt-5.4"),
        max_cycles=7,
        sink_specs=("jsonl:data/cloud.jsonl",),
        adapter_arguments={"search_backend_factory": "custom.factory"},
        runtime_parameters={"max_tokens": 32000},
        custom_parameters={"query": "AI governance"},
        env_vars={},
        secret_references=(),
        remote_command=("python", "-m", "harnessiq.providers.gcloud.runtime"),
    )
    gcp_context = _FakeGcpContext(
        config=GcpAgentConfig(
            agent_name="candidate-a",
            gcp_project_id="proj-123",
            region="us-central1",
            manifest_id="research_sweep",
            runtime_parameters={"max_tokens": 32000},
            custom_parameters={"query": "AI governance"},
        ),
        storage=storage,
        deploy_spec=deploy_spec,
    )

    built_context = HarnessAdapterContext(
        manifest=manifest,
        agent_name="candidate-a",
        memory_path=local_memory_path,
        repo_root=tmp_path / "repo",
        profile=HarnessProfile(manifest_id="research_sweep", agent_name="candidate-a"),
        runtime_parameters={"max_tokens": 32000},
        custom_parameters={"query": "AI governance"},
        bound_credentials={},
    )

    monkeypatch.setattr("harnessiq.providers.gcloud.runtime.get_harness_manifest", lambda _: manifest)
    monkeypatch.setattr("harnessiq.providers.gcloud.runtime._build_adapter", lambda _: adapter)
    monkeypatch.setattr("harnessiq.providers.gcloud.runtime._build_context", lambda **kwargs: built_context)
    monkeypatch.setattr("harnessiq.providers.gcloud.runtime._persist_run_snapshot", lambda context, run_request: context)
    monkeypatch.setattr("harnessiq.providers.gcloud.runtime.seed_cli_environment", lambda repo_root: None)
    monkeypatch.setattr("harnessiq.providers.gcloud.runtime.resolve_agent_model", lambda **kwargs: "resolved-model")
    monkeypatch.setattr(
        "harnessiq.providers.gcloud.runtime.build_runtime_config",
        lambda *, sink_specs: {"sink_specs": sink_specs},
    )

    payload = run_runtime(
        agent_name="candidate-a",
        manifest_id="research_sweep",
        memory_path=memory_path,
        repo_root=tmp_path / "repo",
        gcp_context=gcp_context,
    )

    assert storage.actions == [
        ("download", memory_path, str(local_memory_path)),
        ("upload", memory_path, str(local_memory_path)),
    ]
    assert adapter.seen_args is not None
    assert adapter.seen_args.max_cycles == 7
    assert adapter.seen_args.search_backend_factory == "custom.factory"
    assert payload["status"] == "completed"
    assert payload["runtime"] == {
        "memory_uri": f"gs://bucket/runtime-state/{memory_path}/",
        "synced_from_gcs": True,
        "synced_to_gcs": True,
    }
    assert payload["adapter_result"] == "ok"


def test_run_runtime_syncs_back_on_adapter_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    memory_path = "memory/instagram/candidate-a"
    local_memory_path = tmp_path / "repo" / "memory" / "instagram" / "candidate-a"
    storage = _RecordingStorage(synced_from_gcs=False)
    adapter = _FakeAdapter(should_fail=True)
    manifest = HarnessManifest(
        manifest_id="instagram",
        agent_name="instagram_keyword_discovery",
        display_name="Instagram",
        module_path="tests.fake",
        class_name="FakeAgent",
    )
    deploy_spec = GcpDeploySpec(
        manifest_id="instagram",
        display_name="Instagram",
        agent_name="candidate-a",
        memory_path=memory_path,
        provider_families=(),
        memory_entries=(),
        model_selection=GcpModelSelection(model_profile="ops-fast"),
        max_cycles=None,
        sink_specs=("jsonl:data/cloud.jsonl",),
        adapter_arguments={},
        runtime_parameters={},
        custom_parameters={},
        env_vars={},
        secret_references=(),
        remote_command=("python", "-m", "harnessiq.providers.gcloud.runtime"),
    )
    gcp_context = _FakeGcpContext(
        config=GcpAgentConfig(
            agent_name="candidate-a",
            gcp_project_id="proj-123",
            region="us-central1",
            manifest_id="instagram",
        ),
        storage=storage,
        deploy_spec=deploy_spec,
    )

    built_context = HarnessAdapterContext(
        manifest=manifest,
        agent_name="candidate-a",
        memory_path=local_memory_path,
        repo_root=tmp_path / "repo",
        profile=HarnessProfile(manifest_id="instagram", agent_name="candidate-a"),
        runtime_parameters={},
        custom_parameters={},
        bound_credentials={},
    )

    monkeypatch.setattr("harnessiq.providers.gcloud.runtime.get_harness_manifest", lambda _: manifest)
    monkeypatch.setattr("harnessiq.providers.gcloud.runtime._build_adapter", lambda _: adapter)
    monkeypatch.setattr("harnessiq.providers.gcloud.runtime._build_context", lambda **kwargs: built_context)
    monkeypatch.setattr("harnessiq.providers.gcloud.runtime._persist_run_snapshot", lambda context, run_request: context)
    monkeypatch.setattr("harnessiq.providers.gcloud.runtime.seed_cli_environment", lambda repo_root: None)
    monkeypatch.setattr("harnessiq.providers.gcloud.runtime.resolve_agent_model", lambda **kwargs: "resolved-model")
    monkeypatch.setattr(
        "harnessiq.providers.gcloud.runtime.build_runtime_config",
        lambda *, sink_specs: {"sink_specs": sink_specs},
    )

    with pytest.raises(RuntimeError, match="adapter boom"):
        run_runtime(
            agent_name="candidate-a",
            manifest_id="instagram",
            memory_path=memory_path,
            repo_root=tmp_path / "repo",
            gcp_context=gcp_context,
        )

    assert storage.actions == [
        ("download", memory_path, str(local_memory_path)),
        ("upload", memory_path, str(local_memory_path)),
    ]


def test_run_runtime_syncs_back_when_model_resolution_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    memory_path = "memory/research_sweep/candidate-c"
    local_memory_path = tmp_path / "repo" / "memory" / "research_sweep" / "candidate-c"
    storage = _RecordingStorage(synced_from_gcs=True)
    adapter = _FakeAdapter()
    manifest = HarnessManifest(
        manifest_id="research_sweep",
        agent_name="research_sweep_agent",
        display_name="Research Sweep",
        module_path="tests.fake",
        class_name="FakeAgent",
    )
    deploy_spec = GcpDeploySpec(
        manifest_id="research_sweep",
        display_name="Research Sweep",
        agent_name="candidate-c",
        memory_path=memory_path,
        provider_families=(),
        memory_entries=(),
        model_selection=GcpModelSelection(model="openai:gpt-5.4"),
        max_cycles=3,
        sink_specs=(),
        adapter_arguments={},
        runtime_parameters={},
        custom_parameters={"query": "AI governance"},
        env_vars={},
        secret_references=(),
        remote_command=("python", "-m", "harnessiq.providers.gcloud.runtime"),
    )
    gcp_context = _FakeGcpContext(
        config=GcpAgentConfig(
            agent_name="candidate-c",
            gcp_project_id="proj-123",
            region="us-central1",
            manifest_id="research_sweep",
            custom_parameters={"query": "AI governance"},
        ),
        storage=storage,
        deploy_spec=deploy_spec,
    )

    built_context = HarnessAdapterContext(
        manifest=manifest,
        agent_name="candidate-c",
        memory_path=local_memory_path,
        repo_root=tmp_path / "repo",
        profile=HarnessProfile(manifest_id="research_sweep", agent_name="candidate-c"),
        runtime_parameters={},
        custom_parameters={"query": "AI governance"},
        bound_credentials={},
    )

    monkeypatch.setattr("harnessiq.providers.gcloud.runtime.get_harness_manifest", lambda _: manifest)
    monkeypatch.setattr("harnessiq.providers.gcloud.runtime._build_adapter", lambda _: adapter)
    monkeypatch.setattr("harnessiq.providers.gcloud.runtime._build_context", lambda **kwargs: built_context)
    monkeypatch.setattr("harnessiq.providers.gcloud.runtime._persist_run_snapshot", lambda context, run_request: context)
    monkeypatch.setattr("harnessiq.providers.gcloud.runtime.seed_cli_environment", lambda repo_root: None)
    monkeypatch.setattr(
        "harnessiq.providers.gcloud.runtime.resolve_agent_model",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("model resolution failed")),
    )
    monkeypatch.setattr(
        "harnessiq.providers.gcloud.runtime.build_runtime_config",
        lambda *, sink_specs: {"sink_specs": sink_specs},
    )

    with pytest.raises(RuntimeError, match="model resolution failed"):
        run_runtime(
            agent_name="candidate-c",
            manifest_id="research_sweep",
            memory_path=memory_path,
            repo_root=tmp_path / "repo",
            gcp_context=gcp_context,
        )

    assert storage.actions == [
        ("download", memory_path, str(local_memory_path)),
        ("upload", memory_path, str(local_memory_path)),
    ]


def test_runtime_main_emits_success_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "harnessiq.providers.gcloud.runtime.run_runtime",
        lambda **kwargs: {
            "agent": kwargs["agent_name"],
            "manifest_id": kwargs["manifest_id"],
            "memory_path": kwargs["memory_path"],
            "status": "completed",
        },
    )

    stdout = io.StringIO()
    with redirect_stdout(stdout):
        exit_code = main(
            [
                "--agent",
                "candidate-a",
                "--manifest-id",
                "research_sweep",
                "--memory-path",
                "memory/research_sweep/candidate-a",
            ]
        )

    assert exit_code == 0
    payload = json.loads(stdout.getvalue())
    assert payload["status"] == "completed"
    assert payload["manifest_id"] == "research_sweep"
