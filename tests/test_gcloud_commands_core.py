from harnessiq.providers.gcloud import GcpAgentConfig
from harnessiq.providers.gcloud import commands as cmd
from harnessiq.providers.gcloud.commands import (
    BucketSpec,
    ExecutionOptions,
    JobSpec,
    ScheduleSpec,
    SecretRef,
    SecretSpec,
    ServiceAccountSpec,
    flags,
)


def test_job_spec_from_config_copies_runtime_fields() -> None:
    config = GcpAgentConfig(
        agent_name="candidate-a",
        gcp_project_id="proj-123",
        region="us-central1",
        cpu="2",
        memory="1Gi",
        task_timeout_seconds=7200,
        max_retries=3,
        parallelism=4,
        task_count=5,
        env_vars={"HARNESSIQ_AGENT_MODULE": "harnessiq.agents.linkedin"},
        secrets=[{"env_var": "ANTHROPIC_API_KEY", "secret_name": "HARNESSIQ_ANTHROPIC_API_KEY"}],
        service_account_email="runner@proj-123.iam.gserviceaccount.com",
    )

    spec = JobSpec.from_config(config)

    assert spec.job_name == config.job_name
    assert spec.image_url == config.image_url
    assert spec.region == "us-central1"
    assert spec.cpu == "2"
    assert spec.memory == "1Gi"
    assert spec.task_timeout_seconds == 7200
    assert spec.max_retries == 3
    assert spec.parallelism == 4
    assert spec.task_count == 5
    assert spec.env_vars == {"HARNESSIQ_AGENT_MODULE": "harnessiq.agents.linkedin"}
    assert spec.secrets == [SecretRef("ANTHROPIC_API_KEY", "HARNESSIQ_ANTHROPIC_API_KEY")]
    assert spec.service_account_email == "runner@proj-123.iam.gserviceaccount.com"


def test_parameter_dataclass_defaults_are_stable() -> None:
    assert ExecutionOptions().env_overrides == {}
    assert ScheduleSpec(
        scheduler_job_name="job",
        location="us-central1",
        cron_expression="0 * * * *",
        http_uri="https://example.test/run",
        service_account_email="runner@example.test",
    ).timezone == "UTC"
    assert SecretSpec(secret_name="secret", project_id="proj").replication == "automatic"
    assert ServiceAccountSpec(sa_id="runner", project_id="proj").display_name == ""
    assert BucketSpec(bucket_name="bucket", location="us-central1").uniform_access is True


def test_format_helpers_and_common_flags() -> None:
    assert flags.region_flag("us-central1") == ["--region=us-central1"]
    assert flags.location_flag("us-east1") == ["--location=us-east1"]
    assert flags.format_json() == ["--format=json"]
    assert flags.format_value("name") == ["--format=value(name)"]
    assert flags.quiet() == ["--quiet"]
    assert flags.limit_flag(25) == ["--limit=25"]
    assert flags.filter_flag("name:run.googleapis.com") == ["--filter=name:run.googleapis.com"]
    assert flags.async_flag() == ["--async"]
    assert flags.wait_flag() == ["--wait"]


def test_job_capacity_flag_omissions_match_design_invariants() -> None:
    assert flags.parallelism_flag(0) == []
    assert flags.parallelism_flag(8) == ["--parallelism=8"]
    assert flags.task_count_flag(1) == []
    assert flags.task_count_flag(3) == ["--tasks=3"]
    assert flags.service_account_flag("") == []
    assert flags.service_account_flag("runner@example.test") == ["--service-account=runner@example.test"]


def test_env_var_flags_skip_empty_and_preserve_pair_order() -> None:
    assert flags.set_env_vars_flag({}) == []
    assert flags.update_env_vars_flag({}) == []
    assert flags.remove_env_vars_flag([]) == []
    assert flags.clear_env_vars_flag() == ["--clear-env-vars"]
    assert flags.set_env_vars_flag({"FOO": "bar", "BAZ": "qux"}) == ["--set-env-vars=FOO=bar,BAZ=qux"]
    assert flags.update_env_vars_flag({"FOO": "bar"}) == ["--update-env-vars=FOO=bar"]
    assert flags.remove_env_vars_flag(["FOO", "BAR"]) == ["--remove-env-vars=FOO,BAR"]


def test_secret_flags_emit_one_flag_per_secret() -> None:
    secrets = [
        SecretRef("ANTHROPIC_API_KEY", "HARNESSIQ_ANTHROPIC_API_KEY"),
        SecretRef("LINKEDIN_EMAIL", "HARNESSIQ_LINKEDIN_EMAIL", version="5"),
    ]

    assert flags.set_secrets_flag(secrets) == [
        "--set-secrets=ANTHROPIC_API_KEY=HARNESSIQ_ANTHROPIC_API_KEY:latest",
        "--set-secrets=LINKEDIN_EMAIL=HARNESSIQ_LINKEDIN_EMAIL:5",
    ]
    assert flags.remove_secrets_flag([]) == []
    assert flags.remove_secrets_flag(["ANTHROPIC_API_KEY"]) == ["--remove-secrets=ANTHROPIC_API_KEY"]
    assert flags.secret_flag("HARNESSIQ_ANTHROPIC_API_KEY") == ["--secret=HARNESSIQ_ANTHROPIC_API_KEY"]
    assert flags.version_flag() == ["--version=latest"]
    assert flags.data_file_stdin_flag() == ["--data-file=-"]


def test_service_specific_flags_cover_scheduler_storage_and_monitoring() -> None:
    assert flags.image_flag("image-url") == ["--image=image-url"]
    assert flags.cpu_flag("2") == ["--cpu=2"]
    assert flags.memory_flag("1Gi") == ["--memory=1Gi"]
    assert flags.timeout_flag(900) == ["--task-timeout=900s"]
    assert flags.retries_flag(4) == ["--max-retries=4"]
    assert flags.schedule_flag("0 */4 * * *") == ["--schedule=0 */4 * * *"]
    assert flags.timezone_flag("America/Indianapolis") == ["--time-zone=America/Indianapolis"]
    assert flags.uri_flag("https://example.test") == ["--uri=https://example.test"]
    assert flags.http_method_flag() == ["--http-method=POST"]
    assert flags.oauth_sa_flag("runner@example.test") == ["--oauth-service-account-email=runner@example.test"]
    assert flags.message_body_flag() == ["--message-body={}"]
    assert flags.description_flag("") == []
    assert flags.description_flag("nightly job") == ["--description=nightly job"]
    assert flags.replication_policy_flag() == ["--replication-policy=automatic"]
    assert flags.storage_location_flag("us-central1") == ["--location=us-central1"]
    assert flags.uniform_bucket_level_access_flag() == ["--uniform-bucket-level-access"]
    assert flags.member_flag("serviceAccount:runner@example.test") == ["--member=serviceAccount:runner@example.test"]
    assert flags.role_flag("roles/logging.logWriter") == ["--role=roles/logging.logWriter"]
    assert flags.display_name_flag("") == []
    assert flags.display_name_flag("HarnessIQ Runner") == ["--display-name=HarnessIQ Runner"]
    assert flags.repository_format_flag() == ["--repository-format=docker"]
    assert flags.tag_flag("us-central1-docker.pkg.dev/proj/repo/image:latest") == [
        "--tag=us-central1-docker.pkg.dev/proj/repo/image:latest"
    ]
    assert flags.order_flag() == ["--order=desc"]
    assert flags.freshness_flag("7d") == ["--freshness=7d"]
    assert flags.channel_type_flag("email") == ["--type=email"]
    assert flags.channel_labels_flag({"email_address": "ops@example.test"}) == [
        "--channel-labels=email_address=ops@example.test"
    ]
    assert flags.condition_filter_flag('resource.type="cloud_run_job"') == [
        '--condition-filter=resource.type="cloud_run_job"'
    ]
    assert flags.notification_channels_flag([]) == []
    assert flags.notification_channels_flag(["channels/123", "channels/456"]) == [
        "--notification-channels=channels/123,channels/456"
    ]


def test_flags_module_does_not_define_project_flag() -> None:
    assert not hasattr(flags, "project_flag")


def test_commands_package_exports_public_core_types() -> None:
    assert cmd.JobSpec is JobSpec
    assert cmd.SecretRef is SecretRef
    assert cmd.flags is flags
