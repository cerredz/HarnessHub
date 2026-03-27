from __future__ import annotations

import pytest
from pathlib import Path

from harnessiq.cli.adapters.context import HarnessAdapterContext
from harnessiq.cli.builders import HarnessCliLifecycleBuilder, LinkedInCliBuilder
from harnessiq.config import HarnessProfile, HarnessProfileStore
from harnessiq.shared.harness_manifest import HarnessManifest, HarnessParameterSpec
from harnessiq.shared.harness_manifests import get_harness_manifest


class _StubAdapter:
    def __init__(
        self,
        *,
        native_runtime: dict[str, object] | None = None,
        native_custom: dict[str, object] | None = None,
    ) -> None:
        self.native_runtime = native_runtime or {}
        self.native_custom = native_custom or {}
        self.prepared_contexts: list[HarnessAdapterContext] = []
        self.synchronized_contexts: list[HarnessAdapterContext] = []

    def prepare(self, context: HarnessAdapterContext) -> None:
        self.prepared_contexts.append(context)
        context.memory_path.mkdir(parents=True, exist_ok=True)

    def load_native_parameters(self, context: HarnessAdapterContext) -> tuple[dict[str, object], dict[str, object]]:
        return dict(self.native_runtime), dict(self.native_custom)

    def synchronize_profile(self, context: HarnessAdapterContext) -> None:
        self.synchronized_contexts.append(context)


def _manifest() -> HarnessManifest:
    return HarnessManifest(
        manifest_id="demo",
        agent_name="demo_agent",
        display_name="Demo Harness",
        module_path="demo.module",
        class_name="DemoAgent",
        runtime_parameters=(
            HarnessParameterSpec("max_tokens", "integer", "Maximum tokens.", default=8000),
            HarnessParameterSpec("notify_on_pause", "boolean", "Pause notifications.", default=True),
        ),
        custom_parameters=(
            HarnessParameterSpec("team", "string", "Owning team.", default="default-team"),
        ),
    )


def test_lifecycle_builder_build_context_seeds_from_native_state_and_resolves_defaults(tmp_path: Path) -> None:
    builder = HarnessCliLifecycleBuilder(cwd=tmp_path)
    adapter = _StubAdapter(
        native_runtime={"max_tokens": 2048},
        native_custom={"team": "native-team"},
    )

    context = builder.build_context(
        manifest=_manifest(),
        adapter=adapter,
        agent_name="alpha",
        incoming_runtime={},
        incoming_custom={"team": "cli-team"},
        persist_profile=False,
        memory_root=str(tmp_path / "memory"),
    )

    assert len(adapter.prepared_contexts) == 1
    assert len(adapter.synchronized_contexts) == 1
    assert context.profile.runtime_parameters == {"max_tokens": 2048}
    assert context.runtime_parameters == {
        "max_tokens": 2048,
        "notify_on_pause": True,
    }
    assert context.profile.custom_parameters == {"team": "cli-team"}
    assert context.custom_parameters == {"team": "cli-team"}
    assert not (context.memory_path / ".harnessiq-profile.json").exists()


def test_lifecycle_builder_build_context_prefers_persisted_profile_over_native_seed(tmp_path: Path) -> None:
    manifest = _manifest()
    memory_path = tmp_path / "memory" / "beta"
    memory_path.mkdir(parents=True)
    HarnessProfileStore(memory_path).save(
        HarnessProfile(
            manifest_id=manifest.manifest_id,
            agent_name="beta",
            runtime_parameters={"max_tokens": 4096},
            custom_parameters={"team": "persisted-team"},
        )
    )
    builder = HarnessCliLifecycleBuilder(cwd=tmp_path)
    adapter = _StubAdapter(
        native_runtime={"max_tokens": 1024},
        native_custom={"team": "native-team"},
    )

    context = builder.build_context(
        manifest=manifest,
        adapter=adapter,
        agent_name="beta",
        incoming_runtime={"notify_on_pause": False},
        incoming_custom={},
        persist_profile=False,
        memory_path=memory_path,
    )

    assert context.profile.runtime_parameters == {
        "max_tokens": 4096,
        "notify_on_pause": False,
    }
    assert context.runtime_parameters == {
        "max_tokens": 4096,
        "notify_on_pause": False,
    }
    assert context.profile.custom_parameters == {"team": "persisted-team"}


def test_lifecycle_builder_persists_profile_when_requested(tmp_path: Path) -> None:
    builder = HarnessCliLifecycleBuilder(cwd=tmp_path)
    adapter = _StubAdapter(native_runtime={"max_tokens": 1024})

    context = builder.build_context(
        manifest=_manifest(),
        adapter=adapter,
        agent_name="gamma",
        incoming_runtime={},
        incoming_custom={},
        persist_profile=True,
        memory_root=str(tmp_path / "memory"),
    )

    profile_store = HarnessProfileStore(context.memory_path)
    saved_profile = profile_store.load(manifest_id=context.manifest.manifest_id, agent_name="gamma")

    assert profile_store.profile_path.exists()
    assert saved_profile.runtime_parameters == {"max_tokens": 1024}
    assert (tmp_path / "memory" / "harness_profiles.json").exists()


def test_lifecycle_builder_build_inspection_payload_reports_manifest_metadata() -> None:
    builder = HarnessCliLifecycleBuilder()

    payload = builder.build_inspection_payload(manifest=get_harness_manifest("research_sweep"))

    runtime_index = {entry["key"]: entry for entry in payload["runtime_parameters"]}
    assert payload["harness"] == "research_sweep"
    assert payload["default_memory_root"] == "memory/research_sweep"
    assert runtime_index["max_tokens"]["default"] == 80000
    assert payload["provider_credential_fields"]["serper"][0]["name"] == "api_key"


def test_lifecycle_builder_bind_show_and_test_credentials_round_trip(tmp_path: Path) -> None:
    builder = HarnessCliLifecycleBuilder(cwd=tmp_path)
    manifest = get_harness_manifest("knowt")
    (tmp_path / ".env").write_text(
        "CREATIFY_API_ID=cid_123\nCREATIFY_API_KEY=key_456\n",
        encoding="utf-8",
    )

    bound_payload = builder.bind_credentials(
        manifest=manifest,
        agent_name="channel-a",
        memory_root=tmp_path,
        assignments=[
            "creatify.api_id=CREATIFY_API_ID",
            "creatify.api_key=CREATIFY_API_KEY",
        ],
        description="Channel binding",
    )
    shown_payload = builder.show_credentials(
        manifest=manifest,
        agent_name="channel-a",
        memory_root=tmp_path,
    )
    tested_payload = builder.test_credentials(
        manifest=manifest,
        agent_name="channel-a",
        memory_root=tmp_path,
    )

    assert bound_payload["status"] == "bound"
    assert bound_payload["families"]["creatify"]["api_id"] == "CREATIFY_API_ID"
    assert shown_payload["bound"] is True
    assert shown_payload["description"] == "Channel binding"
    assert shown_payload["families"]["creatify"]["api_key"] == "CREATIFY_API_KEY"
    assert tested_payload["status"] == "resolved"
    assert tested_payload["families"]["creatify"]["api_id"] == "cid_123"
    assert tested_payload["families"]["creatify"]["api_key_masked"].startswith("key")


def test_lifecycle_builder_bind_credentials_rejects_unknown_provider_family(tmp_path: Path) -> None:
    builder = HarnessCliLifecycleBuilder(cwd=tmp_path)

    with pytest.raises(ValueError, match="does not declare provider family 'exa'"):
        builder.bind_credentials(
            manifest=get_harness_manifest("knowt"),
            agent_name="channel-a",
            memory_root=tmp_path,
            assignments=["exa.api_key=EXA_API_KEY"],
            description=None,
        )


def test_linkedin_builder_configure_and_show_round_trip(tmp_path: Path) -> None:
    source_file = tmp_path / "resume.txt"
    source_file.write_text("Resume content", encoding="utf-8")
    builder = LinkedInCliBuilder()

    configured_payload = builder.configure(
        agent_name="candidate-a",
        memory_root=str(tmp_path),
        job_preferences_text="Staff platform roles in New York.",
        job_preferences_file=None,
        user_profile_text="Python and distributed systems.",
        user_profile_file=None,
        agent_identity_text=None,
        agent_identity_file=None,
        additional_prompt_text="Prioritize remote-friendly companies.",
        additional_prompt_file=None,
        runtime_assignments=["max_tokens=2048", "notify_on_pause=false"],
        custom_assignments=["team=platform"],
        import_files=[str(source_file)],
        inline_files=["cover-letter.txt=Hello from the CLI."],
    )
    shown_payload = builder.show(
        agent_name="candidate-a",
        memory_root=str(tmp_path),
    )

    assert configured_payload["status"] == "configured"
    assert configured_payload["runtime_parameters"]["max_tokens"] == 2048
    assert configured_payload["runtime_parameters"]["notify_on_pause"] is False
    assert configured_payload["custom_parameters"]["team"] == "platform"
    assert len(configured_payload["managed_files"]) == 2
    assert shown_payload["job_preferences"] == "Staff platform roles in New York."
    assert "cover-letter.txt" in str(shown_payload["managed_files"])
