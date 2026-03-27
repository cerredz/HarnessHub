from __future__ import annotations

import argparse
import io
import os
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace

import pytest

from harnessiq.cli.adapters.context import HarnessAdapterContext
from harnessiq.cli.runners import (
    HarnessCliLifecycleRunner,
    InstagramCliRunner,
    LinkedInCliRunner,
    ResolvedRunRequest,
)
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


def test_lifecycle_runner_resolve_resume_request_from_snapshot() -> None:
    runner = HarnessCliLifecycleRunner()
    snapshot = HarnessRunSnapshot(
        model="openai:gpt-5.4",
        sink_specs=("jsonl:prior.jsonl",),
        max_cycles=4,
        adapter_arguments={"browser_tools_factory": "prior.factory"},
        runtime_parameters={},
        custom_parameters={},
    )

    run_request = runner.resolve_resume_request_from_snapshot(
        snapshot=snapshot,
        model_factory=None,
        model=None,
        model_profile=None,
        sink_specs=[],
        max_cycles=None,
        run_argument_overrides={"browser_tools_factory": "updated.factory"},
    )

    assert run_request == ResolvedRunRequest(
        model_factory=None,
        model="openai:gpt-5.4",
        model_profile=None,
        sink_specs=("jsonl:prior.jsonl",),
        max_cycles=4,
        adapter_arguments={"browser_tools_factory": "updated.factory"},
    )


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


def test_linkedin_runner_run_uses_saved_browser_session_dir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store_path = tmp_path / "candidate-a"
    browser_data_dir = store_path / "browser-data"
    browser_data_dir.mkdir(parents=True)
    captured_kwargs: dict[str, object] = {}

    class _StubAgent:
        instance_id = "linkedin_job_applier::abc123"
        instance_name = "candidate-a"
        last_run_id = "run-123"

        def run(self, *, max_cycles):
            assert max_cycles == 1
            return SimpleNamespace(cycles_completed=1, pause_reason=None, resets=0, status="completed")

    def _from_memory(**kwargs):
        captured_kwargs.update(kwargs)
        return _StubAgent()

    monkeypatch.setattr("harnessiq.cli.runners.linkedin.seed_cli_environment", lambda _: None)
    monkeypatch.setattr("harnessiq.cli.runners.linkedin.resolve_agent_model", lambda **_: "resolved-model")
    monkeypatch.setattr("harnessiq.cli.runners.linkedin.LinkedInJobApplierAgent.from_memory", _from_memory)
    monkeypatch.delenv("HARNESSIQ_BROWSER_SESSION_DIR", raising=False)

    runner = LinkedInCliRunner()
    stderr = io.StringIO()
    with redirect_stderr(stderr):
        payload = runner.run(
            agent_name="candidate-a",
            memory_root=str(tmp_path),
            model_factory="tests.test_linkedin_cli:create_static_model",
            model=None,
            model_profile=None,
            browser_tools_factory=None,
            runtime_assignments=[],
            sink_specs=[],
            max_cycles=1,
            approval_policy=None,
            allowed_tools=(),
        )

    assert payload["result"]["status"] == "completed"
    assert os.environ["HARNESSIQ_BROWSER_SESSION_DIR"] == str(browser_data_dir.resolve())
    assert captured_kwargs["memory_path"] == store_path
    assert captured_kwargs["browser_tools"] == ()
    assert captured_kwargs["model"] == "resolved-model"
    assert "NO DURABLE LINKEDIN APPLICATION RECORDS FOUND" in stderr.getvalue()


def test_linkedin_runner_init_browser_returns_session_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[tuple[str, Path]] = []

    class _FakeSession:
        def __init__(self, *, session_dir):
            self.session_dir = Path(session_dir)

        def start(self):
            events.append(("start", self.session_dir))

        def stop(self):
            events.append(("stop", self.session_dir))

    monkeypatch.setitem(
        sys.modules,
        "harnessiq.integrations.linkedin_playwright",
        SimpleNamespace(PlaywrightLinkedInSession=_FakeSession),
    )

    runner = LinkedInCliRunner()
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        payload = runner.init_browser(
            agent_name="candidate-b",
            memory_root=str(tmp_path),
            wait_for_exit=lambda: None,
        )

    expected_dir = tmp_path / "candidate-b" / "browser-data"
    assert payload == {
        "agent": "candidate-b",
        "browser_data_dir": str(expected_dir.resolve()),
        "status": "session_saved",
    }
    assert events == [("start", expected_dir), ("stop", expected_dir)]
    assert "Browser session saved to:" in stdout.getvalue()


def test_instagram_runner_run_sets_session_env_and_forwards_overrides(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured_kwargs: dict[str, object] = {}

    class _StubAgent:
        def run(self, *, max_cycles):
            assert max_cycles == 1
            return SimpleNamespace(cycles_completed=1, pause_reason=None, resets=0, status="completed")

        def get_emails(self):
            return ("creator@example.com",)

    def _from_memory(**kwargs):
        captured_kwargs.update(kwargs)
        return _StubAgent()

    monkeypatch.setattr("harnessiq.cli.runners.instagram.seed_cli_environment", lambda _: None)
    monkeypatch.setattr("harnessiq.cli.runners.instagram.resolve_agent_model", lambda **_: "resolved-model")
    monkeypatch.setattr("harnessiq.cli.runners.instagram.load_factory", lambda _: (lambda: "search-backend"))
    monkeypatch.setattr("harnessiq.agents.instagram.InstagramKeywordDiscoveryAgent.from_memory", _from_memory)
    monkeypatch.delenv("HARNESSIQ_INSTAGRAM_SESSION_DIR", raising=False)

    runner = InstagramCliRunner()
    payload = runner.run(
        agent_name="creator-a",
        memory_root=str(tmp_path),
        model_factory="tests.test_instagram_cli:_recording_model_factory",
        model=None,
        model_profile=None,
        search_backend_factory="tests.test_instagram_cli:create_search_backend",
        runtime_overrides={"search_result_limit": 3},
        custom_overrides={"icp_profiles": ["fitness creators"]},
        max_cycles=1,
        approval_policy=None,
        allowed_tools=(),
    )

    expected_session_dir = str((tmp_path / "creator-a" / "browser-data").resolve())
    assert os.environ["HARNESSIQ_INSTAGRAM_SESSION_DIR"] == expected_session_dir
    assert payload["email_count"] == 1
    assert payload["result"]["status"] == "completed"
    assert captured_kwargs["search_backend"] == "search-backend"
    assert captured_kwargs["runtime_overrides"] == {"search_result_limit": 3}
    assert captured_kwargs["custom_overrides"] == {"icp_profiles": ["fitness creators"]}
