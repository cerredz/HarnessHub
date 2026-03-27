from pathlib import Path
from unittest.mock import Mock, call

import pytest

from harnessiq.config import (
    AgentCredentialBinding,
    CredentialEnvReference,
    CredentialsConfigStore,
)
from harnessiq.providers.gcloud import CredentialBridge, GcpAgentConfig


def _config() -> GcpAgentConfig:
    return GcpAgentConfig(
        agent_name="candidate-a",
        gcp_project_id="proj-123",
        region="us-central1",
        manifest_id="research_sweep",
    )


def _write_binding(repo_root: Path, *, references: tuple[CredentialEnvReference, ...]) -> None:
    store = CredentialsConfigStore(repo_root=repo_root)
    store.upsert(
        AgentCredentialBinding(
            agent_name=_config().credential_binding_name,
            references=references,
        )
    )


def test_bridge_discovers_universal_and_bound_credentials_without_leaking_values(tmp_path: Path) -> None:
    tmp_path.joinpath(".env").write_text(
        "ANTHROPIC_API_KEY=sk-ant-test\nSERPER_API_KEY=serper-test\n",
        encoding="utf-8",
    )
    _write_binding(
        tmp_path,
        references=(
            CredentialEnvReference(field_name="serper.api_key", env_var="SERPER_API_KEY"),
        ),
    )

    secret_manager = Mock()
    secret_manager.secret_exists.side_effect = lambda secret_name: secret_name == "HARNESSIQ_ANTHROPIC_API_KEY"
    bridge = CredentialBridge(Mock(), _config(), repo_root=tmp_path, secret_manager=secret_manager)

    entries = bridge.status()
    by_key = {entry.key: entry for entry in entries}

    assert set(by_key) == {"ANTHROPIC_API_KEY", "serper.api_key"}
    assert by_key["ANTHROPIC_API_KEY"].env_var == "ANTHROPIC_API_KEY"
    assert by_key["ANTHROPIC_API_KEY"].in_gcp is True
    assert by_key["serper.api_key"].env_var == "SERPER_API_KEY"
    assert by_key["serper.api_key"].has_local_value is True
    assert by_key["serper.api_key"].status_dict()["local"] is True
    assert "local_value" not in by_key["serper.api_key"].status_dict()


def test_bridge_syncs_missing_credentials_and_registers_secret_references(tmp_path: Path, monkeypatch) -> None:
    tmp_path.joinpath(".env").write_text(
        "ANTHROPIC_API_KEY=sk-ant-test\nSERPER_API_KEY=serper-test\n",
        encoding="utf-8",
    )
    _write_binding(
        tmp_path,
        references=(
            CredentialEnvReference(field_name="serper.api_key", env_var="SERPER_API_KEY"),
        ),
    )

    saved_configs: list[dict[str, object]] = []

    def _fake_save(self, home_dir=None):  # type: ignore[no-untyped-def]
        saved_configs.append(self.as_dict())
        return Path(tmp_path, "saved.json")

    monkeypatch.setattr(GcpAgentConfig, "save", _fake_save)

    secret_manager = Mock()
    secret_manager.secret_exists.return_value = False
    bridge = CredentialBridge(Mock(), _config(), repo_root=tmp_path, secret_manager=secret_manager)

    entries = bridge.sync(interactive=False)
    by_key = {entry.key: entry for entry in entries}

    assert secret_manager.set_secret.call_args_list == [
        call("HARNESSIQ_ANTHROPIC_API_KEY", "sk-ant-test"),
        call("HARNESSIQ_CANDIDATE_A_SERPER_API_KEY", "serper-test"),
    ]
    assert by_key["ANTHROPIC_API_KEY"].in_gcp is True
    assert by_key["serper.api_key"].in_gcp is True
    assert bridge.config.secrets == [
        {"env_var": "ANTHROPIC_API_KEY", "secret_name": "HARNESSIQ_ANTHROPIC_API_KEY"},
        {"env_var": "SERPER_API_KEY", "secret_name": "HARNESSIQ_CANDIDATE_A_SERPER_API_KEY"},
    ]
    assert len(saved_configs) == 1


def test_bridge_non_interactive_sync_fails_when_binding_is_missing(tmp_path: Path) -> None:
    tmp_path.joinpath(".env").write_text("ANTHROPIC_API_KEY=sk-ant-test\n", encoding="utf-8")
    secret_manager = Mock()
    secret_manager.secret_exists.return_value = False
    bridge = CredentialBridge(Mock(), _config(), repo_root=tmp_path, secret_manager=secret_manager)

    with pytest.raises(RuntimeError, match="binding"):
        bridge.sync(interactive=False)

    secret_manager.set_secret.assert_not_called()


def test_bridge_non_interactive_sync_skips_rotation_for_existing_gcp_secret(tmp_path: Path, monkeypatch) -> None:
    tmp_path.joinpath(".env").write_text(
        "ANTHROPIC_API_KEY=sk-ant-test\nSERPER_API_KEY=serper-test\n",
        encoding="utf-8",
    )
    _write_binding(
        tmp_path,
        references=(CredentialEnvReference(field_name="serper.api_key", env_var="SERPER_API_KEY"),),
    )

    monkeypatch.setattr(GcpAgentConfig, "save", lambda self, home_dir=None: Path(tmp_path, "saved.json"))

    secret_manager = Mock()
    secret_manager.secret_exists.return_value = True
    bridge = CredentialBridge(Mock(), _config(), repo_root=tmp_path, secret_manager=secret_manager)

    bridge.sync(interactive=False)

    secret_manager.rotate_secret.assert_not_called()
    assert bridge.config.secrets == [
        {"env_var": "ANTHROPIC_API_KEY", "secret_name": "HARNESSIQ_ANTHROPIC_API_KEY"},
        {"env_var": "SERPER_API_KEY", "secret_name": "HARNESSIQ_CANDIDATE_A_SERPER_API_KEY"},
    ]


def test_bridge_interactive_sync_can_rotate_existing_secret(tmp_path: Path, monkeypatch) -> None:
    tmp_path.joinpath(".env").write_text(
        "ANTHROPIC_API_KEY=sk-ant-test\nSERPER_API_KEY=serper-test\n",
        encoding="utf-8",
    )
    _write_binding(
        tmp_path,
        references=(CredentialEnvReference(field_name="serper.api_key", env_var="SERPER_API_KEY"),),
    )

    monkeypatch.setattr(GcpAgentConfig, "save", lambda self, home_dir=None: Path(tmp_path, "saved.json"))
    monkeypatch.setattr("builtins.input", lambda _: "y")

    secret_manager = Mock()
    secret_manager.secret_exists.return_value = True
    bridge = CredentialBridge(Mock(), _config(), repo_root=tmp_path, secret_manager=secret_manager)

    bridge.sync(interactive=True)

    assert secret_manager.rotate_secret.call_args_list == [
        call("HARNESSIQ_ANTHROPIC_API_KEY", "sk-ant-test"),
        call("HARNESSIQ_CANDIDATE_A_SERPER_API_KEY", "serper-test"),
    ]
