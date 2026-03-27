from unittest.mock import Mock, call

import pytest

from harnessiq.providers.gcloud import GcloudError, GcpAgentConfig
from harnessiq.providers.gcloud import commands as cmd
from harnessiq.providers.gcloud.credentials import SecretManagerProvider
from harnessiq.providers.gcloud.deploy import SchedulerProvider


def _config() -> GcpAgentConfig:
    return GcpAgentConfig(
        agent_name="candidate-a",
        gcp_project_id="proj-123",
        region="us-central1",
        service_account_email="runner@proj-123.iam.gserviceaccount.com",
        schedule_cron="0 */4 * * *",
    )


def _gcloud_error(*parts: str, stderr: str = "not found") -> GcloudError:
    return GcloudError(command=tuple(parts or ("gcloud",)), exit_code=1, stderr=stderr)


def test_scheduler_provider_create_and_update_flows_use_builders() -> None:
    client = Mock()
    provider = SchedulerProvider(client, _config())

    client.run.return_value = "created"
    assert provider.create_schedule(description="Runs candidate-a") == "created"
    client.run.assert_called_once_with(
        cmd.create_schedule(
            cmd.ScheduleSpec(
                scheduler_job_name=_config().scheduler_job_name,
                location=_config().region,
                cron_expression=_config().schedule_cron or "",
                http_uri=provider.job_uri,
                service_account_email=_config().service_account_email or "",
                timezone=_config().timezone,
                description="Runs candidate-a",
            )
        )
    )

    client.reset_mock()
    client.run.return_value = "updated"
    assert provider.update_schedule(cron="0 0 * * *", timezone="America/Indianapolis") == "updated"
    client.run.assert_called_once_with(
        cmd.update_schedule(
            _config().scheduler_job_name,
            _config().region,
            cron="0 0 * * *",
            timezone="America/Indianapolis",
        )
    )


def test_scheduler_provider_deploy_branches_and_control_methods() -> None:
    client = Mock()
    provider = SchedulerProvider(client, _config())

    client.run_json.return_value = {"name": _config().scheduler_job_name}
    client.run.return_value = "updated"
    assert provider.deploy_schedule() == "updated"
    client.run.assert_called_once_with(
        cmd.update_schedule(_config().scheduler_job_name, _config().region, cron=None, timezone=None)
    )

    client.reset_mock(return_value=True, side_effect=True)
    client.run_json.side_effect = _gcloud_error("gcloud", "scheduler")
    client.run.return_value = "created"
    assert provider.deploy_schedule() == "created"
    client.run.assert_called_once()

    client.reset_mock(return_value=True, side_effect=True)
    client.run_json.return_value = {"name": _config().scheduler_job_name}
    assert provider.describe() == {"name": _config().scheduler_job_name}

    client.reset_mock(return_value=True, side_effect=True)
    client.run_json.return_value = [{"name": _config().scheduler_job_name}]
    assert provider.list_schedules() == [{"name": _config().scheduler_job_name}]

    client.reset_mock()
    provider.pause()
    provider.resume()
    provider.run_now()
    provider.delete()
    assert client.run.call_args_list == [
        call(cmd.pause_schedule(_config().scheduler_job_name, _config().region)),
        call(cmd.resume_schedule(_config().scheduler_job_name, _config().region)),
        call(cmd.run_schedule_now(_config().scheduler_job_name, _config().region)),
        call(cmd.delete_schedule(_config().scheduler_job_name, _config().region)),
    ]


def test_scheduler_provider_validates_required_service_account_and_cron() -> None:
    config = GcpAgentConfig(agent_name="candidate-a", gcp_project_id="proj-123", region="us-central1")
    provider = SchedulerProvider(Mock(), config)

    with pytest.raises(ValueError, match="service_account_email"):
        provider.create_schedule()

    config_with_service_account = GcpAgentConfig(
        agent_name="candidate-a",
        gcp_project_id="proj-123",
        region="us-central1",
        service_account_email="runner@proj-123.iam.gserviceaccount.com",
    )
    provider = SchedulerProvider(Mock(), config_with_service_account)
    with pytest.raises(ValueError, match="cron"):
        provider.create_schedule()


def test_scheduler_provider_surfaces_non_not_found_errors() -> None:
    client = Mock()
    provider = SchedulerProvider(client, _config())

    client.run_json.side_effect = _gcloud_error("gcloud", "scheduler", stderr="permission denied")
    with pytest.raises(GcloudError):
        provider.schedule_exists()


def test_secret_manager_provider_set_and_rotate_do_not_leak_values_in_commands() -> None:
    client = Mock()
    provider = SecretManagerProvider(client, _config())
    secret_name = "HARNESSIQ_ANTHROPIC_API_KEY"

    client.run_json.side_effect = _gcloud_error("gcloud", "secrets")
    client.run.return_value = "ok"

    assert provider.set_secret(secret_name, "super-secret") == "ok"
    assert client.run.call_args_list == [
        call(
            cmd.create_secret(
                cmd.SecretSpec(
                    secret_name=secret_name,
                    project_id=_config().gcp_project_id,
                    replication="automatic",
                )
            )
        ),
        call(cmd.add_secret_version(secret_name), input_text="super-secret"),
    ]
    assert all("super-secret" not in " ".join(args[0]) for args, _ in client.run.call_args_list)

    client.reset_mock(return_value=True, side_effect=True)
    client.run.return_value = "rotated"
    assert provider.rotate_secret(secret_name, "new-secret") == "rotated"
    client.run.assert_called_once_with(cmd.add_secret_version(secret_name), input_text="new-secret")


def test_secret_manager_provider_read_and_delete_flows_use_builders() -> None:
    client = Mock()
    provider = SecretManagerProvider(client, _config())
    secret_name = "HARNESSIQ_ANTHROPIC_API_KEY"

    client.run_json.return_value = {"name": secret_name}
    assert provider.secret_exists(secret_name) is True
    assert provider.get_secret(secret_name) == {"name": secret_name}

    client.reset_mock(return_value=True, side_effect=True)
    client.run_json.return_value = [{"name": secret_name}]
    assert provider.list_secrets() == [{"name": secret_name}]
    assert provider.list_secret_versions(secret_name) == [{"name": secret_name}]

    client.reset_mock()
    client.run.return_value = "deleted"
    assert provider.delete_secret(secret_name) == "deleted"
    client.run.assert_called_once_with(cmd.delete_secret(secret_name))

    client.run_json.side_effect = _gcloud_error("gcloud", "secrets", stderr="permission denied")
    with pytest.raises(GcloudError):
        provider.secret_exists(secret_name)
