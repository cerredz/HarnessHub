from pathlib import Path
from unittest.mock import Mock, call

from harnessiq.providers.gcloud import GcpAgentConfig
from harnessiq.providers.gcloud import commands as cmd
from harnessiq.providers.gcloud.infra import BillingProvider
from harnessiq.providers.gcloud.observability import LoggingProvider, MonitoringProvider
from harnessiq.providers.gcloud.storage import CloudStorageProvider


def _config() -> GcpAgentConfig:
    return GcpAgentConfig(
        agent_name="candidate-a",
        gcp_project_id="proj-123",
        region="us-central1",
        service_account_email="runner@proj-123.iam.gserviceaccount.com",
        memory="1Gi",
        cpu="2",
        task_timeout_seconds=600,
        schedule_cron="0 */4 * * *",
        secrets=[{"env_var": "ANTHROPIC_API_KEY", "secret_name": "HARNESSIQ_ANTHROPIC_API_KEY"}],
    )


def test_billing_provider_returns_deterministic_cost_estimate() -> None:
    estimate = BillingProvider(Mock(), _config()).estimate_monthly_cost()

    assert estimate.cloud_run_per_run_usd > 0
    assert estimate.cloud_run_monthly_usd > 0
    assert estimate.scheduler_monthly_usd == 0.1
    assert estimate.secret_manager_monthly_usd > 0
    assert estimate.total_monthly_usd == round(
        estimate.cloud_run_monthly_usd
        + estimate.scheduler_monthly_usd
        + estimate.secret_manager_monthly_usd
        + estimate.artifact_registry_monthly_usd,
        4,
    )
    assert any("Monthly runs: 180" in item for item in estimate.assumptions)
    assert BillingProvider._estimate_monthly_runs("0 */0 * * *") == 30


def test_logging_provider_reads_job_logs_via_command_builders() -> None:
    client = Mock()
    provider = LoggingProvider(client, _config())

    client.run.return_value = "line-1\nline-2"
    assert provider.get_job_logs(execution_name="exec-1", limit=5) == "line-1\nline-2"
    client.run.assert_called_once_with(
        cmd.read_logs_text(
            cmd.LogQuerySpec(
                filter_str=cmd.job_log_filter(_config().job_name, "exec-1"),
                limit=5,
                order="asc",
                freshness=None,
            )
        )
    )

    client.reset_mock()
    client.run_json.return_value = [{"textPayload": "ok"}]
    assert provider.read_json(cmd.LogQuerySpec(filter_str="severity>=ERROR")) == [{"textPayload": "ok"}]
    client.run_json.assert_called_once_with(
        cmd.read_logs_json(cmd.LogQuerySpec(filter_str="severity>=ERROR"))
    )


def test_monitoring_provider_creates_channels_and_failure_alerts() -> None:
    client = Mock()
    provider = MonitoringProvider(client, _config())

    client.run.side_effect = ["channels/123", "policies/456"]
    assert provider.create_failure_alert("ops@example.test") == "policies/456"
    assert client.run.call_args_list == [
        call(
            cmd.create_email_notification_channel(
                "harnessiq candidate-a alerts",
                "ops@example.test",
            )
        ),
        call(
            cmd.create_alert_policy(
                cmd.AlertPolicySpec(
                    display_name=f"harnessiq {_config().job_name} failure",
                    metric_filter=cmd.job_failure_filter(_config().job_name),
                    notification_channels=["channels/123"],
                )
            )
        ),
    ]

    client.reset_mock(return_value=True, side_effect=True)
    client.run_json.return_value = [{"name": "channels/123"}]
    assert provider.list_notification_channels() == [{"name": "channels/123"}]
    assert provider.list_alert_policies() == [{"name": "channels/123"}]

    client.reset_mock(return_value=True, side_effect=True)
    provider.delete_notification_channel("channels/123")
    provider.delete_alert_policy("policies/456")
    assert client.run.call_args_list == [
        call(cmd.delete_notification_channel("channels/123")),
        call(cmd.delete_alert_policy("policies/456")),
    ]


def test_cloud_storage_provider_bucket_and_object_helpers(tmp_path: Path) -> None:
    client = Mock()
    provider = CloudStorageProvider(client, _config())

    client.run.return_value = "created"
    assert provider.create_bucket() == "created"
    client.run.assert_called_once_with(
        cmd.create_bucket(
            cmd.BucketSpec(
                bucket_name="harnessiq-proj-123-agent-memory",
                location="us-central1",
            )
        )
    )

    client.reset_mock()
    client.run.return_value = '{"hello":"world"}'
    assert provider.read_text("gs://bucket/object.txt") == '{"hello":"world"}'

    client.reset_mock()
    client.run.return_value = "uploaded"
    assert provider.write_text("gs://bucket/object.txt", "payload") == "uploaded"
    command = client.run.call_args.args[0]
    assert command[:2] == ["storage", "cp"]
    assert command[-1] == "gs://bucket/object.txt"
    assert not Path(command[2]).exists()

    client.reset_mock()
    client.run.return_value = "gs://bucket/one.txt\ngs://bucket/two.txt\n"
    assert provider.list_objects("gs://bucket") == [
        "gs://bucket/one.txt",
        "gs://bucket/two.txt",
    ]

    client.reset_mock()
    provider.delete_object("gs://bucket/object.txt")
    client.run.assert_called_once_with(cmd.delete_object("gs://bucket/object.txt"))
