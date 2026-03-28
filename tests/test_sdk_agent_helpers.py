from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from harnessiq.agents import (
    build_agent_runtime_config,
    build_output_sinks,
    inspect_harness,
)
from harnessiq.agents import KnowtAgent, LeadsAgent
from harnessiq.config import (
    AgentCredentialBinding,
    CredentialEnvReference,
    CredentialsConfigStore,
    HarnessProfile,
    resolve_harness_credentials,
    seed_environment,
)
from harnessiq.shared.harness_manifests import get_harness_manifest
from harnessiq.shared.leads import LeadICP, LeadRunConfig, LeadsMemoryStore
from harnessiq.utils import ConnectionsConfigStore, JSONLLedgerSink, SinkConnection, SlackSink


def _mock_model() -> MagicMock:
    model = MagicMock()
    model.generate_turn.return_value = MagicMock()
    return model


def test_build_agent_runtime_config_resolves_connections_and_sink_specs(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HARNESSIQ_HOME", str(tmp_path / "home"))
    ConnectionsConfigStore().upsert(
        SinkConnection(
            name="team-slack",
            sink_type="slack",
            config={"webhook_url": "https://example.test/webhook"},
        )
    )

    config = build_agent_runtime_config(
        sink_specs=("jsonl:logs/runs.jsonl",),
        approval_policy="always",
        allowed_tools=("filesystem.read_text_file", "context.*"),
        dynamic_tools_enabled=True,
        dynamic_tool_candidates=("filesystem.read_text_file,context.*",),
        dynamic_tool_top_k=2,
        max_tokens=2048,
        reset_threshold=0.8,
        session_id="sdk-session",
    )

    assert config.max_tokens == 2048
    assert config.reset_threshold == 0.8
    assert config.allowed_tools == ("filesystem.read_text_file", "context.*")
    assert config.tool_selection.enabled is True
    assert config.tool_selection.candidate_tool_keys == ("filesystem.read_text_file", "context.*")
    assert config.session_id == "sdk-session"
    assert any(isinstance(sink, SlackSink) for sink in config.output_sinks)
    assert any(isinstance(sink, JSONLLedgerSink) for sink in config.output_sinks)


def test_inspect_harness_returns_manifest_backed_payload() -> None:
    payload = inspect_harness("research_sweep")

    assert payload["harness"] == "research_sweep"
    assert payload["default_memory_root"] == "memory/research_sweep"
    assert "serper" in payload["provider_credential_fields"]
    assert "type" in payload["runtime_parameters"][0]


def test_build_output_sinks_is_promoted_via_agents_namespace() -> None:
    sinks = build_output_sinks(sink_specs=("jsonl:logs/runs.jsonl",))

    assert len(sinks) == 1
    assert isinstance(sinks[0], JSONLLedgerSink)


def test_seed_environment_public_wrapper_reads_env_files(tmp_path, monkeypatch) -> None:
    (tmp_path / ".env").write_text("XAI_API_KEY=base-key\n", encoding="utf-8")
    (tmp_path / "local.env").write_text("LANGCHAIN_API_KEY=langsmith-key\n", encoding="utf-8")
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)

    applied = seed_environment(tmp_path)

    assert applied["XAI_API_KEY"] == "base-key"
    assert applied["LANGSMITH_API_KEY"] == "langsmith-key"


def test_resolve_harness_credentials_returns_provider_objects(tmp_path) -> None:
    manifest = get_harness_manifest("knowt")
    CredentialsConfigStore(repo_root=tmp_path).upsert(
        AgentCredentialBinding(
            agent_name="harness::knowt::channel-a",
            references=(
                CredentialEnvReference(field_name="creatify.api_id", env_var="CREATIFY_API_ID"),
                CredentialEnvReference(field_name="creatify.api_key", env_var="CREATIFY_API_KEY"),
            ),
        )
    )
    (tmp_path / ".env").write_text(
        "CREATIFY_API_ID=cid_123\nCREATIFY_API_KEY=key_456\n",
        encoding="utf-8",
    )

    resolved = resolve_harness_credentials(manifest, agent_name="channel-a", repo_root=tmp_path)

    assert "creatify" in resolved
    assert resolved["creatify"].api_id == "cid_123"


def test_leads_from_memory_uses_run_config_and_runtime_parameters(tmp_path) -> None:
    store = LeadsMemoryStore(memory_path=tmp_path / "leads")
    store.prepare()
    store.write_run_config(
        LeadRunConfig(
            company_background="We sell workflow tooling.",
            icps=(LeadICP(label="Operations leaders"),),
            platforms=("apollo",),
        )
    )
    store.write_runtime_parameters(
        {
            "max_tokens": 4096,
            "reset_threshold": 0.75,
            "search_summary_every": 7,
            "search_tail_size": 3,
        }
    )

    agent = LeadsAgent.from_memory(
        model=_mock_model(),
        memory_path=store.memory_path,
        tools=(),
        instance_name="ops",
    )

    assert agent.config.max_tokens == 4096
    assert agent.config.reset_threshold == 0.75
    assert agent.config.run_config.search_summary_every == 7
    assert agent.config.run_config.search_tail_size == 3
    assert agent.instance_name == "ops"


def test_knowt_from_profile_uses_profile_runtime_parameters(tmp_path) -> None:
    profile = HarnessProfile(
        manifest_id="knowt",
        agent_name="channel-a",
        runtime_parameters={"max_tokens": 3210, "reset_threshold": 0.7},
    )

    agent = KnowtAgent.from_profile(
        profile=profile,
        model=_mock_model(),
        memory_path=tmp_path / "knowt" / "channel-a",
    )

    assert agent.config.max_tokens == 3210
    assert agent.config.reset_threshold == 0.7
