from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from harnessiq.cli.main import build_parser, main
from harnessiq.providers.gcloud.infra.billing import CostEstimate


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


def test_gcloud_execute_wait_and_async_are_mutually_exclusive() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["gcloud", "execute", "--agent", "candidate-a", "--wait", "--async"])
    assert exc_info.value.code == 2


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


def test_gcloud_build_deploy_and_schedule_commands_delegate_to_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact_registry = SimpleNamespace(
        build_image=Mock(return_value="build submitted"),
        repository_path="us-central1-docker.pkg.dev/proj-123/harnessiq",
    )
    cloud_run = SimpleNamespace(deploy_job=Mock(return_value="job deployed"))
    scheduler = SimpleNamespace(deploy_schedule=Mock(return_value="schedule deployed"))
    fake_context = SimpleNamespace(
        config=SimpleNamespace(
            agent_name="candidate-a",
            gcp_project_id="proj-123",
            region="us-central1",
            image_url="us-central1-docker.pkg.dev/proj-123/harnessiq/candidate-a:latest",
            job_name="harnessiq-candidate-a",
            schedule_cron="0 */4 * * *",
            scheduler_job_name="harnessiq-candidate-a-schedule",
            service_account_email="runner@proj-123.iam.gserviceaccount.com",
            timezone="UTC",
        ),
        deploy=SimpleNamespace(
            artifact_registry=artifact_registry,
            cloud_run=cloud_run,
            scheduler=scheduler,
        ),
    )
    monkeypatch.setattr("harnessiq.cli.gcloud.commands._load_context", lambda agent_name, dry_run=False: fake_context)

    build_payload = _run_json_command(
        ["gcloud", "build", "--agent", "candidate-a", "--source-dir", "src", "--dry-run"]
    )
    deploy_payload = _run_json_command(["gcloud", "deploy", "--agent", "candidate-a"])
    schedule_payload = _run_json_command(
        [
            "gcloud",
            "schedule",
            "--agent",
            "candidate-a",
            "--cron",
            "0 0 * * *",
            "--timezone",
            "America/Indianapolis",
            "--description",
            "Nightly run",
            "--dry-run",
        ]
    )

    artifact_registry.build_image.assert_called_once_with(source_dir="src")
    cloud_run.deploy_job.assert_called_once_with()
    scheduler.deploy_schedule.assert_called_once_with(
        service_account_email=None,
        cron="0 0 * * *",
        timezone="America/Indianapolis",
        description="Nightly run",
    )
    assert build_payload["status"] == "dry_run"
    assert deploy_payload["status"] == "deployed"
    assert schedule_payload["status"] == "dry_run"


def test_gcloud_execute_logs_and_cost_commands_emit_json(monkeypatch: pytest.MonkeyPatch) -> None:
    cloud_run = SimpleNamespace(execute=Mock(return_value="execution-123"))
    logging_provider = SimpleNamespace(get_job_logs=Mock(return_value="line-1\nline-2"))
    billing_provider = SimpleNamespace(
        estimate_monthly_cost=Mock(
            return_value=CostEstimate(
                cloud_run_per_run_usd=0.02,
                cloud_run_monthly_usd=1.2,
                scheduler_monthly_usd=0.1,
                secret_manager_monthly_usd=0.06,
                artifact_registry_monthly_usd=0.05,
                total_monthly_usd=1.41,
                assumptions=["Monthly runs: 30"],
            )
        )
    )
    fake_context = SimpleNamespace(
        config=SimpleNamespace(
            agent_name="candidate-a",
            gcp_project_id="proj-123",
            region="us-central1",
            job_name="harnessiq-candidate-a",
        ),
        deploy=SimpleNamespace(cloud_run=cloud_run),
        observability=SimpleNamespace(logging=logging_provider),
        infra=SimpleNamespace(billing=billing_provider),
    )
    monkeypatch.setattr("harnessiq.cli.gcloud.commands._load_context", lambda agent_name, dry_run=False: fake_context)

    execute_payload = _run_json_command(
        [
            "gcloud",
            "execute",
            "--agent",
            "candidate-a",
            "--wait",
            "--task-count",
            "3",
            "--timeout-seconds",
            "900",
            "--env-override",
            "FOO=bar",
            "--env-override",
            "BAZ=qux",
        ]
    )
    logs_payload = _run_json_command(
        [
            "gcloud",
            "logs",
            "--agent",
            "candidate-a",
            "--execution-name",
            "exec-1",
            "--limit",
            "5",
            "--freshness",
            "1d",
        ]
    )
    cost_payload = _run_json_command(["gcloud", "cost", "--agent", "candidate-a"])

    cloud_run.execute.assert_called_once_with(
        wait=True,
        async_=False,
        task_count=3,
        timeout_override=900,
        env_overrides={"FOO": "bar", "BAZ": "qux"},
    )
    logging_provider.get_job_logs.assert_called_once_with(
        execution_name="exec-1",
        limit=5,
        order="asc",
        freshness="1d",
    )
    billing_provider.estimate_monthly_cost.assert_called_once_with()
    assert execute_payload["status"] == "executed"
    assert execute_payload["env_overrides"] == {"FOO": "bar", "BAZ": "qux"}
    assert logs_payload["logs"] == "line-1\nline-2"
    assert cost_payload["estimate"]["total_monthly_usd"] == 1.41


def test_gcloud_schedule_propagates_provider_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    scheduler = SimpleNamespace(deploy_schedule=Mock(side_effect=ValueError("cron must be provided")))
    fake_context = SimpleNamespace(
        config=SimpleNamespace(
            agent_name="candidate-a",
            gcp_project_id="proj-123",
            region="us-central1",
            schedule_cron=None,
            scheduler_job_name="harnessiq-candidate-a-schedule",
            service_account_email="runner@proj-123.iam.gserviceaccount.com",
            timezone="UTC",
        ),
        deploy=SimpleNamespace(scheduler=scheduler),
    )
    monkeypatch.setattr("harnessiq.cli.gcloud.commands._load_context", lambda agent_name, dry_run=False: fake_context)

    with pytest.raises(ValueError, match="cron must be provided"):
        main(["gcloud", "schedule", "--agent", "candidate-a"])


def test_gcloud_credentials_sync_propagates_bridge_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    bridge = SimpleNamespace(sync=Mock(side_effect=RuntimeError("missing credential binding")))
    fake_context = SimpleNamespace(
        config=SimpleNamespace(agent_name="candidate-a", gcp_project_id="proj-123", region="us-central1"),
        credentials=SimpleNamespace(bridge=bridge),
    )
    monkeypatch.setattr("harnessiq.cli.gcloud.commands._load_context", lambda agent_name, dry_run=False: fake_context)

    with pytest.raises(RuntimeError, match="missing credential binding"):
        main(["gcloud", "credentials", "sync", "--agent", "candidate-a", "--non-interactive"])


def test_gcloud_documented_workflow_runs_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    config = SimpleNamespace(
        agent_name="candidate-a",
        gcp_project_id="proj-123",
        region="us-central1",
        image_url="us-central1-docker.pkg.dev/proj-123/harnessiq/candidate-a:latest",
        job_name="harnessiq-candidate-a",
        schedule_cron="0 */4 * * *",
        scheduler_job_name="harnessiq-candidate-a-schedule",
        service_account_email="runner@proj-123.iam.gserviceaccount.com",
        timezone="UTC",
        save=Mock(return_value=Path("/tmp/candidate-a.json")),
    )
    bridge = SimpleNamespace(
        sync=Mock(return_value=[SimpleNamespace(status_dict=lambda: {"key": "ANTHROPIC_API_KEY", "gcp": True})]),
        status=Mock(return_value=[SimpleNamespace(status_dict=lambda: {"key": "ANTHROPIC_API_KEY", "gcp": True})]),
    )
    fake_context = SimpleNamespace(
        config=config,
        health=SimpleNamespace(
            validate_all=Mock(
                return_value=[SimpleNamespace(name="gcloud CLI installed", passed=True, message="ok", fix=None)]
            )
        ),
        credentials=SimpleNamespace(bridge=bridge),
        deploy=SimpleNamespace(
            artifact_registry=SimpleNamespace(
                build_image=Mock(return_value="build submitted"),
                repository_path="us-central1-docker.pkg.dev/proj-123/harnessiq",
            ),
            cloud_run=SimpleNamespace(
                deploy_job=Mock(return_value="job deployed"),
                execute=Mock(return_value="execution-123"),
            ),
            scheduler=SimpleNamespace(deploy_schedule=Mock(return_value="schedule deployed")),
        ),
        observability=SimpleNamespace(logging=SimpleNamespace(get_job_logs=Mock(return_value="line-1"))),
        infra=SimpleNamespace(
            billing=SimpleNamespace(
                estimate_monthly_cost=Mock(
                    return_value=CostEstimate(
                        cloud_run_per_run_usd=0.02,
                        cloud_run_monthly_usd=1.2,
                        scheduler_monthly_usd=0.1,
                        secret_manager_monthly_usd=0.06,
                        artifact_registry_monthly_usd=0.05,
                        total_monthly_usd=1.41,
                        assumptions=["Monthly runs: 30"],
                    )
                )
            )
        ),
    )
    monkeypatch.setattr("harnessiq.cli.gcloud.commands._create_init_context", lambda args: fake_context)
    monkeypatch.setattr("harnessiq.cli.gcloud.commands._load_context", lambda agent_name, dry_run=False: fake_context)
    monkeypatch.setattr(
        "harnessiq.cli.gcloud.commands.GcpAgentConfig.config_path_for",
        lambda agent_name: Path("/tmp") / f"{agent_name}.json",
    )

    init_payload = _run_json_command(
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
    build_payload = _run_json_command(["gcloud", "build", "--agent", "candidate-a", "--source-dir", "."])
    deploy_payload = _run_json_command(["gcloud", "deploy", "--agent", "candidate-a"])
    schedule_payload = _run_json_command(["gcloud", "schedule", "--agent", "candidate-a", "--cron", "0 */4 * * *"])
    execute_payload = _run_json_command(["gcloud", "execute", "--agent", "candidate-a", "--wait"])
    logs_payload = _run_json_command(["gcloud", "logs", "--agent", "candidate-a"])
    cost_payload = _run_json_command(["gcloud", "cost", "--agent", "candidate-a"])

    assert init_payload["status"] == "initialized"
    assert build_payload["status"] == "built"
    assert deploy_payload["status"] == "deployed"
    assert schedule_payload["status"] == "scheduled"
    assert execute_payload["status"] == "executed"
    assert logs_payload["status"] == "ok"
    assert cost_payload["status"] == "estimated"
    bridge.sync.assert_called_once_with(interactive=False, dry_run=False)


def _run_json_command(argv: list[str]) -> dict[str, object]:
    stdout = io.StringIO()
    with redirect_stdout(stdout):
        exit_code = main(argv)
    assert exit_code == 0
    return json.loads(stdout.getvalue())
