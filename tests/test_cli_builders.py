from __future__ import annotations

from pathlib import Path

from harnessiq.cli.adapters.context import HarnessAdapterContext
from harnessiq.cli.builders import HarnessCliLifecycleBuilder
from harnessiq.config import HarnessProfile, HarnessProfileStore
from harnessiq.shared.harness_manifest import HarnessManifest, HarnessParameterSpec


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
