from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from harnessiq.cli.main import build_parser, main


def test_gcloud_top_level_command_is_registered() -> None:
    parser = build_parser()
    args, _ = parser.parse_known_args(["gcloud", "health", "--agent", "candidate-a"])

    assert args.command == "gcloud"
    assert args.gcloud_command == "health"


def test_gcloud_credentials_subcommands_are_registered() -> None:
    parser = build_parser()
    args, _ = parser.parse_known_args(["gcloud", "credentials", "sync", "--agent", "candidate-a"])

    assert args.command == "gcloud"
    assert args.gcloud_command == "credentials"
    assert args.gcloud_credentials_command == "sync"


def test_gcloud_help_path_exits_cleanly() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["gcloud", "--help"])
    assert exc_info.value.code == 0


def test_gcloud_root_command_prints_help() -> None:
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        exit_code = main(["gcloud"])

    assert exit_code == 0
    assert "Manage Google Cloud deployment configuration and operations" in stdout.getvalue()


def test_gcloud_health_emits_json(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_context = SimpleNamespace(
        config=SimpleNamespace(agent_name="candidate-a", gcp_project_id="proj-123", region="us-central1"),
        health=SimpleNamespace(
            validate_all=Mock(
                return_value=[
                    SimpleNamespace(
                        name="gcloud CLI installed",
                        passed=True,
                        message="gcloud CLI found",
                        fix=None,
                    )
                ]
            )
        ),
    )

    monkeypatch.setattr("harnessiq.cli.gcloud.commands._load_context", lambda agent_name, dry_run=False: fake_context)

    payload = _run_json_command(["gcloud", "health", "--agent", "candidate-a"])

    assert payload["agent"] == "candidate-a"
    assert payload["status"] == "healthy"
    assert payload["health"] == [
        {
            "fix": None,
            "message": "gcloud CLI found",
            "name": "gcloud CLI installed",
            "passed": True,
        }
    ]
    fake_context.health.validate_all.assert_called_once_with(fail_fast=False)


def test_gcloud_credentials_status_emits_json(monkeypatch: pytest.MonkeyPatch) -> None:
    entry = SimpleNamespace(
        status_dict=lambda: {
            "env_var": "ANTHROPIC_API_KEY",
            "gcp": True,
            "key": "ANTHROPIC_API_KEY",
            "local": True,
            "required": True,
            "secret_name": "HARNESSIQ_ANTHROPIC_API_KEY",
            "source": "repo_env",
        }
    )
    fake_context = SimpleNamespace(
        config=SimpleNamespace(agent_name="candidate-a", gcp_project_id="proj-123", region="us-central1"),
        credentials=SimpleNamespace(bridge=SimpleNamespace(status=Mock(return_value=[entry]))),
    )
    monkeypatch.setattr("harnessiq.cli.gcloud.commands._load_context", lambda agent_name, dry_run=False: fake_context)

    payload = _run_json_command(["gcloud", "credentials", "status", "--agent", "candidate-a"])

    assert payload["status"] == "ok"
    assert payload["credentials"][0]["secret_name"] == "HARNESSIQ_ANTHROPIC_API_KEY"
    fake_context.credentials.bridge.status.assert_called_once_with()


def test_gcloud_credentials_sync_passes_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    entry = SimpleNamespace(status_dict=lambda: {"key": "ANTHROPIC_API_KEY", "local": True, "gcp": False})
    bridge = SimpleNamespace(sync=Mock(return_value=[entry]))
    fake_context = SimpleNamespace(
        config=SimpleNamespace(agent_name="candidate-a", gcp_project_id="proj-123", region="us-central1"),
        credentials=SimpleNamespace(bridge=bridge),
    )
    monkeypatch.setattr("harnessiq.cli.gcloud.commands._load_context", lambda agent_name, dry_run=False: fake_context)
    monkeypatch.setattr(
        "harnessiq.cli.gcloud.commands.GcpAgentConfig.config_path_for",
        lambda agent_name: Path("/tmp") / f"{agent_name}.json",
    )

    payload = _run_json_command(
        ["gcloud", "credentials", "sync", "--agent", "candidate-a", "--non-interactive", "--dry-run"]
    )

    bridge.sync.assert_called_once_with(interactive=False, dry_run=True)
    assert payload["status"] == "dry_run"
    assert payload["config_path"].endswith("candidate-a.json")


def test_gcloud_credentials_set_and_remove_delegate_to_bridge(monkeypatch: pytest.MonkeyPatch) -> None:
    bridge = SimpleNamespace(add_custom=Mock(), remove=Mock())
    fake_context = SimpleNamespace(
        config=SimpleNamespace(agent_name="candidate-a", gcp_project_id="proj-123", region="us-central1"),
        credentials=SimpleNamespace(bridge=bridge),
    )
    monkeypatch.setattr("harnessiq.cli.gcloud.commands._load_context", lambda agent_name, dry_run=False: fake_context)
    monkeypatch.setattr(
        "harnessiq.cli.gcloud.commands.GcpAgentConfig.config_path_for",
        lambda agent_name: Path("/tmp") / f"{agent_name}.json",
    )

    set_payload = _run_json_command(
        [
            "gcloud",
            "credentials",
            "set",
            "--agent",
            "candidate-a",
            "--env-var",
            "SERPER_API_KEY",
            "--secret-name",
            "HARNESSIQ_CANDIDATE_A_SERPER_API_KEY",
            "--value",
            "serper-test",
        ]
    )
    remove_payload = _run_json_command(
        [
            "gcloud",
            "credentials",
            "remove",
            "--agent",
            "candidate-a",
            "--env-var",
            "SERPER_API_KEY",
            "--delete-from-gcp",
            "--dry-run",
        ]
    )

    bridge.add_custom.assert_called_once_with(
        "SERPER_API_KEY",
        "HARNESSIQ_CANDIDATE_A_SERPER_API_KEY",
        value="serper-test",
        dry_run=False,
    )
    bridge.remove.assert_called_once_with(
        "SERPER_API_KEY",
        delete_from_gcp=True,
        dry_run=True,
    )
    assert set_payload["status"] == "registered"
    assert remove_payload["status"] == "dry_run"


def test_gcloud_credentials_check_emits_local_auth_health(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = SimpleNamespace(
        check_gcloud_installed=Mock(
            return_value=SimpleNamespace(name="gcloud CLI installed", passed=True, message="found", fix=None)
        ),
        check_gcloud_auth=Mock(
            return_value=SimpleNamespace(name="gcloud CLI auth", passed=True, message="user@example.test", fix=None)
        ),
        check_adc=Mock(
            return_value=SimpleNamespace(name="Application Default Credentials (ADC)", passed=True, message="ok", fix=None)
        ),
        check_anthropic_key_local=Mock(
            return_value=SimpleNamespace(name="ANTHROPIC_API_KEY (local)", passed=False, message="missing", fix="export")
        ),
    )
    monkeypatch.setattr("harnessiq.cli.gcloud.commands._build_local_health_provider", lambda: provider)

    payload = _run_json_command(["gcloud", "credentials", "check"])

    assert payload["scope"] == "credentials_auth"
    assert payload["status"] == "unhealthy"
    assert [item["name"] for item in payload["health"]] == [
        "gcloud CLI installed",
        "gcloud CLI auth",
        "Application Default Credentials (ADC)",
        "ANTHROPIC_API_KEY (local)",
    ]


def test_gcloud_init_runs_health_save_and_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    config = SimpleNamespace(
        agent_name="candidate-a",
        gcp_project_id="proj-123",
        region="us-central1",
        save=Mock(return_value=Path("/tmp/candidate-a.json")),
    )
    bridge = SimpleNamespace(sync=Mock(return_value=[SimpleNamespace(status_dict=lambda: {"key": "ANTHROPIC_API_KEY"})]))
    fake_context = SimpleNamespace(
        config=config,
        health=SimpleNamespace(
            validate_all=Mock(
                return_value=[
                    SimpleNamespace(name="gcloud CLI installed", passed=True, message="ok", fix=None),
                ]
            )
        ),
        credentials=SimpleNamespace(bridge=bridge),
    )
    monkeypatch.setattr("harnessiq.cli.gcloud.commands._create_init_context", lambda args: fake_context)
    monkeypatch.setattr(
        "harnessiq.cli.gcloud.commands.GcpAgentConfig.config_path_for",
        lambda agent_name: Path("/tmp") / f"{agent_name}.json",
    )

    payload = _run_json_command(
        [
            "gcloud",
            "init",
            "--agent",
            "candidate-a",
            "--project-id",
            "proj-123",
            "--region",
            "us-central1",
            "--manifest-id",
            "research_sweep",
            "--non-interactive",
        ]
    )

    config.save.assert_called_once_with()
    fake_context.health.validate_all.assert_called_once_with(fail_fast=False)
    bridge.sync.assert_called_once_with(interactive=False, dry_run=False)
    assert payload["status"] == "initialized"
    assert payload["config_path"].endswith("candidate-a.json")


def test_gcloud_credentials_sync_propagates_bridge_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    bridge = SimpleNamespace(sync=Mock(side_effect=RuntimeError("missing credential binding")))
    fake_context = SimpleNamespace(
        config=SimpleNamespace(agent_name="candidate-a", gcp_project_id="proj-123", region="us-central1"),
        credentials=SimpleNamespace(bridge=bridge),
    )
    monkeypatch.setattr("harnessiq.cli.gcloud.commands._load_context", lambda agent_name, dry_run=False: fake_context)

    with pytest.raises(RuntimeError, match="missing credential binding"):
        main(["gcloud", "credentials", "sync", "--agent", "candidate-a", "--non-interactive"])


def _run_json_command(argv: list[str]) -> dict[str, object]:
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        exit_code = main(argv)
    assert exit_code == 0
    return json.loads(stdout.getvalue())
