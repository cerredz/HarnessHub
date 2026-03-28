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
from harnessiq.cli.builders import ExaOutreachCliBuilder, LeadsCliBuilder, ProspectingCliBuilder, ResearchSweepCliBuilder
from harnessiq.cli.runners import (
    ExaOutreachCliRunner,
    HarnessCliLifecycleRunner,
    InstagramCliRunner,
    LeadsCliRunner,
    LinkedInCliRunner,
    ProspectingCliRunner,
    ResearchSweepCliRunner,
    ResolvedRunRequest,
)
from harnessiq.config import HarnessProfile, HarnessRunSnapshot
from harnessiq.shared.dtos import (
    HarnessAdapterResponseDTO,
    HarnessCommandPayloadDTO,
    HarnessProfileViewDTO,
    HarnessRunResultDTO,
)
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
    captured_runtime_kwargs: dict[str, object] = {}

    class _StubAdapter:
        def run(self, *, args, context, model, runtime_config):
            del args, context
            assert model == "resolved-model"
            assert runtime_config == "runtime-config"
            return HarnessAdapterResponseDTO(result=HarnessRunResultDTO(status="completed"))

    class _StubRunner(HarnessCliLifecycleRunner):
        def build_runtime_config(self, *args, **kwargs):  # type: ignore[override]
            del args
            captured_runtime_kwargs.update(kwargs)
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
        args=argparse.Namespace(
            approval_policy=None,
            allowed_tools=(),
            dynamic_tools=True,
            dynamic_tool_candidates=("filesystem.*",),
            dynamic_tool_top_k=2,
            dynamic_tool_embedding_model="openai:text-embedding-3-small",
        ),
        context=context,
        run_request=ResolvedRunRequest(
            model_factory="tests.test_platform_cli:create_static_model",
            model=None,
            model_profile=None,
            sink_specs=(),
            max_cycles=1,
            adapter_arguments={"search_backend_factory": "factory.path"},
        ),
        base_payload=HarnessCommandPayloadDTO(
            agent="alpha",
            harness="demo",
            memory_path=str((tmp_path / "memory").resolve()),
            credential_binding_name="harness::demo::alpha",
            bound_credential_families=(),
            profile=HarnessProfileViewDTO(
                config_path=str((tmp_path / "memory" / ".harnessiq-profile.json").resolve()),
                runtime_parameters={},
                custom_parameters={},
                effective_runtime_parameters={},
                effective_custom_parameters={},
            ),
        ),
        source_snapshot=None,
    )

    assert exit_code == 0
    assert len(captured) == 1
    payload = captured[0]
    assert payload["agent"] == "alpha"
    assert payload["harness"] == "demo"
    assert payload["credential_binding_name"] == "harness::demo::alpha"
    assert payload["bound_credential_families"] == []
    assert payload["profile"]["run_count"] == 0
    assert payload["resume"] == {
        "adapter_arguments": {"search_backend_factory": "factory.path"},
        "max_cycles": 1,
        "model_factory": "tests.test_platform_cli:create_static_model",
        "sink_specs": [],
    }
    assert payload["result"] == {
        "cycles_completed": None,
        "pause_reason": None,
        "resets": None,
        "status": "completed",
    }
    assert captured_runtime_kwargs == {
        "approval_policy": None,
        "allowed_tools": (),
        "dynamic_tools_enabled": True,
        "dynamic_tool_candidates": ("filesystem.*",),
        "dynamic_tool_top_k": 2,
        "dynamic_tool_embedding_model": "openai:text-embedding-3-small",
    }


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


def test_leads_runner_run_forwards_factories_and_overrides(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured_kwargs: dict[str, object] = {}

    class _StubStorageBackend:
        def start_run(self, run_id: str, metadata: dict[str, object]) -> None:
            del run_id, metadata

        def finish_run(self, run_id: str, completed_at: str) -> None:
            del run_id, completed_at

        def save_leads(self, run_id: str, icp_key: str, leads, metadata=None):
            del run_id, icp_key, leads, metadata
            return ()

        def has_seen_lead(self, dedupe_key: str) -> bool:
            del dedupe_key
            return False

        def list_leads(self, *, icp_key: str | None = None):
            del icp_key
            return []

        def current_run_id(self) -> str | None:
            return None

    class _StubAgent:
        def run(self, *, max_cycles):
            assert max_cycles == 1
            return SimpleNamespace(cycles_completed=1, pause_reason=None, resets=0, status="completed")

    def _fake_load_factory(spec: str):
        if spec == "tools:factory":
            return lambda: ("provider-tool",)
        if spec == "creds:factory":
            return lambda: {"token": "abc"}
        if spec == "client:factory":
            return lambda: {"client": "apollo"}
        if spec == "storage:factory":
            return lambda: _StubStorageBackend()
        raise AssertionError(f"Unexpected factory spec: {spec}")

    def _fake_leads_agent(**kwargs):
        captured_kwargs.update(kwargs)
        return _StubAgent()

    monkeypatch.setattr("harnessiq.cli.runners.leads.seed_cli_environment", lambda _: None)
    monkeypatch.setattr("harnessiq.cli.runners.leads.resolve_agent_model", lambda **_: "resolved-model")
    monkeypatch.setattr("harnessiq.cli.runners.leads.load_factory", _fake_load_factory)
    monkeypatch.setattr("harnessiq.cli.runners.leads.LeadsAgent", _fake_leads_agent)

    builder = LeadsCliBuilder()
    builder.configure(
        agent_name="campaign-a",
        memory_root=str(tmp_path),
        company_background_text="We sell outbound infrastructure to B2B SaaS revenue teams.",
        company_background_file=None,
        icp_texts=["VP Sales at Series A SaaS companies"],
        icp_files=[],
        platforms=["apollo"],
        runtime_assignments=["search_summary_every=25"],
    )

    runner = LeadsCliRunner()
    payload = runner.run(
        agent_name="campaign-a",
        memory_root=str(tmp_path),
        model_factory="tests.test_leads_cli:create_saving_model",
        model=None,
        model_profile=None,
        provider_tools_factory="tools:factory",
        provider_credentials_factories=["apollo=creds:factory"],
        provider_client_factories=["apollo=client:factory"],
        storage_backend_factory="storage:factory",
        runtime_assignments=["search_summary_every=7", "max_tokens=1024"],
        max_cycles=1,
        approval_policy=None,
        allowed_tools=(),
    )

    assert payload["result"]["status"] == "completed"
    assert captured_kwargs["search_summary_every"] == 7
    assert captured_kwargs["max_tokens"] == 1024
    assert captured_kwargs["tools"] == ("provider-tool",)
    assert captured_kwargs["provider_credentials"] == {"apollo": {"token": "abc"}}
    assert captured_kwargs["provider_clients"] == {"apollo": {"client": "apollo"}}


def test_leads_runner_run_requires_existing_configuration(tmp_path: Path) -> None:
    runner = LeadsCliRunner()

    with pytest.raises(
        ValueError,
        match="Leads configuration not found\\. Run `harnessiq leads configure` before `harnessiq leads run`\\.",
    ):
        runner.run(
            agent_name="campaign-a",
            memory_root=str(tmp_path),
            model_factory="tests.test_leads_cli:create_saving_model",
            model=None,
            model_profile=None,
            provider_tools_factory=None,
            provider_credentials_factories=[],
            provider_client_factories=[],
            storage_backend_factory=None,
            runtime_assignments=[],
            max_cycles=1,
            approval_policy=None,
            allowed_tools=(),
        )


def test_prospecting_runner_run_sets_session_env_and_forwards_overrides(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured_kwargs: dict[str, object] = {}

    class _StubAgent:
        last_run_id = "run-123"

        def run(self, *, max_cycles):
            assert max_cycles == 2
            return SimpleNamespace(cycles_completed=2, pause_reason=None, resets=1, status="completed")

    def _from_memory(**kwargs):
        captured_kwargs.update(kwargs)
        return _StubAgent()

    monkeypatch.setattr("harnessiq.cli.runners.prospecting.seed_cli_environment", lambda _: None)
    monkeypatch.setattr("harnessiq.cli.runners.prospecting.resolve_agent_model", lambda **_: "resolved-model")
    monkeypatch.setattr("harnessiq.cli.runners.prospecting.load_factory", lambda _: (lambda: ("browser-tool",)))
    monkeypatch.setattr("harnessiq.cli.runners.prospecting.GoogleMapsProspectingAgent.from_memory", _from_memory)
    monkeypatch.delenv("HARNESSIQ_PROSPECTING_SESSION_DIR", raising=False)

    builder = ProspectingCliBuilder()
    builder.configure(
        agent_name="nj-dentists",
        memory_root=str(tmp_path),
        company_description_text="Owner-operated dental practices in New Jersey.",
        company_description_file=None,
        agent_identity_text=None,
        agent_identity_file=None,
        additional_prompt_text=None,
        additional_prompt_file=None,
        eval_system_prompt_file=None,
        runtime_assignments=["max_tokens=4096"],
        custom_assignments=["max_searches_per_run=12"],
    )

    runner = ProspectingCliRunner()
    payload = runner.run(
        agent_name="nj-dentists",
        memory_root=str(tmp_path),
        model_factory="tests.test_prospecting_cli:_recording_model_factory",
        model=None,
        model_profile=None,
        browser_tools_factory="tests.test_prospecting_cli:create_browser_tools",
        runtime_assignments=["max_tokens=2048"],
        custom_assignments=["max_searches_per_run=3"],
        sink_specs=["jsonl:out.jsonl"],
        max_cycles=2,
        approval_policy=None,
        allowed_tools=(),
    )

    expected_session_dir = str((tmp_path / "nj-dentists" / "browser-data").resolve())
    assert os.environ["HARNESSIQ_PROSPECTING_SESSION_DIR"] == expected_session_dir
    assert payload["ledger_run_id"] == "run-123"
    assert payload["result"]["status"] == "completed"
    assert captured_kwargs["browser_tools"] == ("browser-tool",)
    assert captured_kwargs["runtime_overrides"] == {"max_tokens": 2048}
    assert captured_kwargs["custom_overrides"] == {"max_searches_per_run": 3}


def test_prospecting_runner_init_browser_returns_session_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[tuple[str, Path, str, bool]] = []

    class _FakeSession:
        def __init__(self, *, session_dir, channel, headless):
            self.session_dir = Path(session_dir)
            self.channel = channel
            self.headless = headless

        def start(self):
            events.append(("start", self.session_dir, self.channel, self.headless))

        def stop(self):
            events.append(("stop", self.session_dir, self.channel, self.headless))

    monkeypatch.setitem(
        sys.modules,
        "harnessiq.integrations.google_maps_playwright",
        SimpleNamespace(PlaywrightGoogleMapsSession=_FakeSession),
    )

    runner = ProspectingCliRunner()
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        payload = runner.init_browser(
            agent_name="nj-dentists",
            memory_root=str(tmp_path),
            channel="chrome",
            headless=False,
            wait_for_exit=lambda: None,
        )

    expected_dir = tmp_path / "nj-dentists" / "browser-data"
    assert payload == {
        "agent": "nj-dentists",
        "browser_data_dir": str(expected_dir.resolve()),
        "status": "session_saved",
    }
    assert events == [
        ("start", expected_dir, "chrome", False),
        ("stop", expected_dir, "chrome", False),
    ]
    assert "Open Google Maps" in stdout.getvalue()


def test_exa_outreach_runner_run_forwards_factories_and_search_only_flag(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured_kwargs: dict[str, object] = {}

    class _StubAgent:
        instance_id = "exa_outreach::abc123"
        instance_name = "outreach-a"
        last_run_id = "run-ledger-1"
        _current_run_id = "run_1"

        def run(self, *, max_cycles):
            assert max_cycles == 1
            return SimpleNamespace(cycles_completed=1, pause_reason=None, resets=0, status="completed")

    def _fake_load_factory(spec: str):
        if spec == "exa:factory":
            return lambda: {"api_key": "exa"}
        if spec == "resend:factory":
            return lambda: {"api_key": "resend"}
        if spec == "emails:factory":
            return lambda: [
                {
                    "id": "t1",
                    "title": "T",
                    "subject": "S",
                    "description": "D",
                    "actual_email": "Body",
                }
            ]
        raise AssertionError(f"Unexpected factory spec: {spec}")

    def _fake_agent(**kwargs):
        captured_kwargs.update(kwargs)
        return _StubAgent()

    builder = ExaOutreachCliBuilder()
    builder.configure(
        agent_name="outreach-a",
        memory_root=str(tmp_path),
        query_text="VPs of Engineering",
        query_file=None,
        agent_identity_text=None,
        agent_identity_file=None,
        additional_prompt_text=None,
        additional_prompt_file=None,
        runtime_assignments=["max_tokens=50000"],
    )

    monkeypatch.setattr("harnessiq.cli.runners.exa_outreach.seed_cli_environment", lambda _: None)
    monkeypatch.setattr("harnessiq.cli.runners.exa_outreach.resolve_agent_model", lambda **_: "resolved-model")
    monkeypatch.setattr("harnessiq.cli.runners.exa_outreach.load_factory", _fake_load_factory)
    monkeypatch.setattr("harnessiq.cli.runners.exa_outreach.ExaOutreachAgent", _fake_agent)

    runner = ExaOutreachCliRunner()
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        payload = runner.run(
            agent_name="outreach-a",
            memory_root=str(tmp_path),
            model_factory="tests.test_exa_outreach_cli:mock_model",
            model=None,
            model_profile=None,
            exa_credentials_factory="exa:factory",
            resend_credentials_factory="resend:factory",
            email_data_factory="emails:factory",
            search_only=False,
            runtime_assignments=["reset_threshold=0.75"],
            sink_specs=[],
            max_cycles=1,
            approval_policy=None,
            allowed_tools=(),
        )

    assert payload["run_id"] == "run_1"
    assert payload["ledger_run_id"] == "run-ledger-1"
    assert payload["result"]["status"] == "completed"
    assert captured_kwargs["search_query"] == "VPs of Engineering"
    assert captured_kwargs["max_tokens"] == 50000
    assert captured_kwargs["reset_threshold"] == 0.75
    assert len(captured_kwargs["email_data"]) == 1
    assert "No run file found for run_1." in stdout.getvalue()


def test_exa_outreach_runner_run_requires_delivery_factories(tmp_path: Path) -> None:
    runner = ExaOutreachCliRunner()

    with pytest.raises(ValueError, match="--resend-credentials-factory is required unless --search-only is set\\."):
        runner.run(
            agent_name="outreach-a",
            memory_root=str(tmp_path),
            model_factory="tests.test_exa_outreach_cli:mock_model",
            model=None,
            model_profile=None,
            exa_credentials_factory="exa:factory",
            resend_credentials_factory=None,
            email_data_factory=None,
            search_only=False,
            runtime_assignments=[],
            sink_specs=[],
            max_cycles=1,
            approval_policy=None,
            allowed_tools=(),
        )


def test_research_sweep_runner_run_uses_supplied_serper_credentials_factory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured_kwargs: dict[str, object] = {}

    class _StubAgent:
        instance_id = "instance-1"
        instance_name = "sweep-a"
        last_run_id = "ledger-1"

        def run(self, *, max_cycles):
            assert max_cycles == 2
            return SimpleNamespace(cycles_completed=2, pause_reason=None, resets=0, status="completed")

    def _fake_load_factory(spec: str):
        if spec == "mod:serper":
            return lambda: SimpleNamespace(api_key="cli-serper-key")
        raise AssertionError(f"Unexpected factory spec: {spec}")

    def _from_memory(**kwargs):
        captured_kwargs.update(kwargs)
        return _StubAgent()

    builder = ResearchSweepCliBuilder()
    builder.configure(
        agent_name="sweep-a",
        memory_root=str(tmp_path),
        query_text="few-shot learning for protein folding",
        query_file=None,
        additional_prompt_text=None,
        additional_prompt_file=None,
        runtime_assignments=[],
        custom_assignments=[],
    )

    monkeypatch.setattr("harnessiq.cli.runners.research_sweep.seed_cli_environment", lambda _: None)
    monkeypatch.setattr("harnessiq.cli.runners.research_sweep.resolve_agent_model", lambda **_: "resolved-model")
    monkeypatch.setattr("harnessiq.cli.runners.research_sweep.load_factory", _fake_load_factory)
    monkeypatch.setattr("harnessiq.cli.runners.research_sweep.ResearchSweepAgent.from_memory", _from_memory)

    runner = ResearchSweepCliRunner()
    payload = runner.run(
        agent_name="sweep-a",
        memory_root=str(tmp_path),
        model_factory="mod:model",
        serper_credentials_factory="mod:serper",
        runtime_assignments=[],
        custom_assignments=[],
        sink_specs=[],
        max_cycles=2,
    )

    assert payload["result"]["status"] == "completed"
    assert payload["instance_name"] == "sweep-a"
    assert captured_kwargs["serper_credentials"].api_key == "cli-serper-key"
    assert captured_kwargs["custom_overrides"]["query"] == "few-shot learning for protein folding"


def test_research_sweep_runner_run_uses_bound_serper_credentials_when_factory_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured_kwargs: dict[str, object] = {}

    class _ResolvedBinding:
        def as_dict(self) -> dict[str, str]:
            return {"serper.api_key": "resolved-serper-key"}

    class _CredentialStore:
        def __init__(self, *, repo_root):
            self.repo_root = repo_root

        def load(self):
            return self

        def binding_for(self, binding_name: str):
            assert "research_sweep" in binding_name
            return "binding"

        def resolve_binding(self, binding):
            assert binding == "binding"
            return _ResolvedBinding()

    class _Spec:
        def build_credentials(self, family_values: dict[str, str]):
            return SimpleNamespace(api_key=family_values["api_key"])

    class _StubAgent:
        instance_id = "instance-2"
        instance_name = "sweep-b"
        last_run_id = "ledger-2"

        def run(self, *, max_cycles):
            assert max_cycles == 1
            return SimpleNamespace(cycles_completed=1, pause_reason=None, resets=0, status="completed")

    def _from_memory(**kwargs):
        captured_kwargs.update(kwargs)
        return _StubAgent()

    builder = ResearchSweepCliBuilder()
    builder.configure(
        agent_name="sweep-b",
        memory_root=str(tmp_path),
        query_text="structure-based drug design",
        query_file=None,
        additional_prompt_text=None,
        additional_prompt_file=None,
        runtime_assignments=[],
        custom_assignments=[],
    )

    monkeypatch.setattr("harnessiq.cli.runners.research_sweep.seed_cli_environment", lambda _: None)
    monkeypatch.setattr("harnessiq.cli.runners.research_sweep.resolve_agent_model", lambda **_: "resolved-model")
    monkeypatch.setattr("harnessiq.cli.runners.research_sweep.CredentialsConfigStore", _CredentialStore)
    monkeypatch.setattr("harnessiq.cli.runners.research_sweep.get_provider_credential_spec", lambda _: _Spec())
    monkeypatch.setattr("harnessiq.cli.runners.research_sweep.ResearchSweepAgent.from_memory", _from_memory)

    runner = ResearchSweepCliRunner()
    payload = runner.run(
        agent_name="sweep-b",
        memory_root=str(tmp_path),
        model_factory="mod:model",
        serper_credentials_factory=None,
        runtime_assignments=[],
        custom_assignments=[],
        sink_specs=[],
        max_cycles=1,
    )

    assert payload["result"]["status"] == "completed"
    assert captured_kwargs["serper_credentials"].api_key == "resolved-serper-key"
