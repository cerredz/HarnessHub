from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from harnessiq.cli.adapters.context import HarnessAdapterContext
from harnessiq.cli.runners import HarnessCliLifecycleRunner, ResolvedRunRequest
from harnessiq.config import HarnessProfile, HarnessRunSnapshot
from harnessiq.shared.harness_manifest import HarnessManifest


def _manifest() -> HarnessManifest:
    return HarnessManifest(
        manifest_id="demo",
        agent_name="demo_agent",
        display_name="Demo Harness",
        module_path="demo.module",
        class_name="DemoAgent",
    )


def _profile() -> HarnessProfile:
    return HarnessProfile(
        manifest_id="demo",
        agent_name="alpha",
        runtime_parameters={"max_tokens": 2048},
        custom_parameters={},
    )


def test_lifecycle_runner_resolve_run_request_for_new_run() -> None:
    runner = HarnessCliLifecycleRunner()
    args = argparse.Namespace(
        model_factory=None,
        model="openai:gpt-5.4",
        model_profile=None,
        sink=["jsonl:out.jsonl"],
        max_cycles=3,
        search_backend_factory="tests.test_platform_cli:create_instagram_search_backend",
    )

    run_request = runner.resolve_run_request(
        args=args,
        profile=_profile(),
        resume_requested=False,
        resume_snapshot=None,
        requested_run_number=None,
        run_argument_defaults={"search_backend_factory": "default.factory"},
        adapter_argument_names=("search_backend_factory",),
        run_argument_overrides={},
    )

    assert run_request == ResolvedRunRequest(
        model_factory=None,
        model="openai:gpt-5.4",
        model_profile=None,
        sink_specs=("jsonl:out.jsonl",),
        max_cycles=3,
        adapter_arguments={"search_backend_factory": "tests.test_platform_cli:create_instagram_search_backend"},
    )


def test_lifecycle_runner_resolve_run_request_merges_resume_snapshot_overrides() -> None:
    runner = HarnessCliLifecycleRunner()
    snapshot = HarnessRunSnapshot(
        model_factory="tests.test_platform_cli:create_static_model",
        sink_specs=("jsonl:prior.jsonl",),
        max_cycles=2,
        adapter_arguments={"search_backend_factory": "prior.factory"},
        runtime_parameters={},
        custom_parameters={},
    )
    args = argparse.Namespace(
        model_factory=None,
        model=None,
        model_profile=None,
        sink=[],
        max_cycles=None,
        search_backend_factory="updated.factory",
    )

    run_request = runner.resolve_run_request(
        args=args,
        profile=HarnessProfile(
            manifest_id="demo",
            agent_name="alpha",
            runtime_parameters={},
            custom_parameters={},
            last_run=snapshot,
            run_history=(snapshot,),
        ),
        resume_requested=True,
        resume_snapshot=snapshot,
        requested_run_number=1,
        run_argument_defaults={"search_backend_factory": "prior.factory"},
        adapter_argument_names=("search_backend_factory",),
        run_argument_overrides={"extra_flag": True},
    )

    assert run_request.model_factory == "tests.test_platform_cli:create_static_model"
    assert run_request.sink_specs == ("jsonl:prior.jsonl",)
    assert run_request.max_cycles == 2
    assert run_request.adapter_arguments == {
        "search_backend_factory": "updated.factory",
        "extra_flag": True,
    }


def test_lifecycle_runner_execute_run_emits_expected_payload(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: list[dict[str, object]] = []

    class _StubAdapter:
        def run(self, *, args, context, model, runtime_config):
            del args, context
            assert model == "resolved-model"
            assert runtime_config == "runtime-config"
            return {"result": {"status": "completed"}}

    class _StubRunner(HarnessCliLifecycleRunner):
        def build_runtime_config(self, *args, **kwargs):  # type: ignore[override]
            del args, kwargs
            return "runtime-config"

    monkeypatch.setattr("harnessiq.cli.runners.lifecycle.resolve_agent_model", lambda **_: "resolved-model")
    monkeypatch.setattr("harnessiq.cli.runners.lifecycle.emit_json", lambda payload: captured.append(payload))
    monkeypatch.setattr("harnessiq.cli.runners.lifecycle.seed_cli_environment", lambda _: None)

    runner = _StubRunner()
    context = HarnessAdapterContext(
        manifest=_manifest(),
        agent_name="alpha",
        memory_path=tmp_path / "memory",
        repo_root=tmp_path,
        profile=_profile(),
        runtime_parameters={},
        custom_parameters={},
        bound_credentials={},
    )

    exit_code = runner.execute_run(
        adapter=_StubAdapter(),
        args=argparse.Namespace(approval_policy=None, allowed_tools=()),
        context=context,
        run_request=ResolvedRunRequest(
            model_factory="tests.test_platform_cli:create_static_model",
            model=None,
            model_profile=None,
            sink_specs=(),
            max_cycles=1,
            adapter_arguments={"search_backend_factory": "factory.path"},
        ),
        base_payload={"agent": "alpha"},
        source_snapshot=None,
    )

    assert exit_code == 0
    assert captured == [
        {
            "agent": "alpha",
            "resume": {
                "adapter_arguments": {"search_backend_factory": "factory.path"},
                "max_cycles": 1,
                "model_factory": "tests.test_platform_cli:create_static_model",
                "sink_specs": [],
            },
            "result": {"status": "completed"},
        }
    ]
