from harnessiq.providers.gcloud import commands as cmd
from harnessiq.providers.gcloud.commands import auth, iam, logging_, monitoring, storage
from harnessiq.providers.gcloud.commands.params import AlertPolicySpec, BucketSpec, IamBinding, LogQuerySpec, ServiceAccountSpec


def test_auth_builders_emit_expected_commands() -> None:
    assert auth.list_active_accounts() == [
        "auth",
        "list",
        "--filter=status:ACTIVE",
        "--format=value(account)",
    ]
    assert auth.print_access_token() == ["auth", "print-access-token"]
    assert auth.print_adc_token() == ["auth", "application-default", "print-access-token"]
    assert auth.revoke_adc() == ["auth", "application-default", "revoke"]
    assert auth.enable_services(["run.googleapis.com", "iam.googleapis.com"]) == [
        "services",
        "enable",
        "run.googleapis.com",
        "iam.googleapis.com",
    ]
    assert auth.list_enabled_services() == ["services", "list", "--format=value(name)"]
    assert auth.list_enabled_services("name:run.googleapis.com") == [
        "services",
        "list",
        "--filter=name:run.googleapis.com",
        "--format=value(name)",
    ]
    assert auth.is_service_enabled("run.googleapis.com") == [
        "services",
        "list",
        "--filter=name:run.googleapis.com",
        "--format=value(name)",
    ]
    assert auth.get_project_number("proj-123") == [
        "projects",
        "describe",
        "proj-123",
        "--format=value(projectNumber)",
    ]
    assert auth.get_current_project() == ["config", "get-value", "project"]
    assert auth.set_current_project("proj-123") == ["config", "set", "project", "proj-123"]


def test_iam_builders_emit_formats_and_quiet_flags() -> None:
    spec = ServiceAccountSpec(
        sa_id="harnessiq-runner",
        project_id="proj-123",
        display_name="HarnessIQ Runner",
        description="Runs jobs",
    )
    binding = IamBinding(
        project_id="proj-123",
        member="serviceAccount:runner@proj-123.iam.gserviceaccount.com",
        role="roles/logging.logWriter",
    )

    assert iam.create_service_account(spec) == [
        "iam",
        "service-accounts",
        "create",
        "harnessiq-runner",
        "--display-name=HarnessIQ Runner",
        "--description=Runs jobs",
    ]
    assert iam.describe_service_account("runner@proj-123.iam.gserviceaccount.com") == [
        "iam",
        "service-accounts",
        "describe",
        "runner@proj-123.iam.gserviceaccount.com",
        "--format=json",
    ]
    assert iam.list_service_accounts() == ["iam", "service-accounts", "list", "--format=json"]
    assert iam.delete_service_account("runner@proj-123.iam.gserviceaccount.com") == [
        "iam",
        "service-accounts",
        "delete",
        "runner@proj-123.iam.gserviceaccount.com",
        "--quiet",
    ]
    assert iam.add_iam_binding(binding) == [
        "projects",
        "add-iam-policy-binding",
        "proj-123",
        "--member=serviceAccount:runner@proj-123.iam.gserviceaccount.com",
        "--role=roles/logging.logWriter",
        "--quiet",
    ]
    assert iam.remove_iam_binding(binding) == [
        "projects",
        "remove-iam-policy-binding",
        "proj-123",
        "--member=serviceAccount:runner@proj-123.iam.gserviceaccount.com",
        "--role=roles/logging.logWriter",
        "--quiet",
    ]
    assert iam.get_iam_policy("proj-123") == ["projects", "get-iam-policy", "proj-123", "--format=json"]
    assert iam.describe_project("proj-123") == [
        "projects",
        "describe",
        "proj-123",
        "--format=value(projectNumber)",
    ]


def test_storage_builders_emit_expected_bucket_and_object_commands() -> None:
    assert storage.create_bucket(BucketSpec(bucket_name="bucket-1", location="us-central1")) == [
        "storage",
        "buckets",
        "create",
        "gs://bucket-1",
        "--location=us-central1",
        "--uniform-bucket-level-access",
        "--quiet",
    ]
    assert storage.create_bucket(
        BucketSpec(bucket_name="bucket-2", location="us-east1", uniform_access=False)
    ) == [
        "storage",
        "buckets",
        "create",
        "gs://bucket-2",
        "--location=us-east1",
        "--quiet",
    ]
    assert storage.describe_bucket("bucket-1") == [
        "storage",
        "buckets",
        "describe",
        "gs://bucket-1",
        "--format=json",
    ]
    assert storage.delete_bucket("bucket-1") == [
        "storage",
        "buckets",
        "delete",
        "gs://bucket-1",
        "--quiet",
    ]
    assert storage.cat_object("gs://bucket-1/memory.json") == ["storage", "cat", "gs://bucket-1/memory.json"]
    assert storage.copy_to_gcs("memory.json", "gs://bucket-1/memory.json") == [
        "storage",
        "cp",
        "memory.json",
        "gs://bucket-1/memory.json",
    ]
    assert storage.copy_from_gcs("gs://bucket-1/memory.json", "memory.json") == [
        "storage",
        "cp",
        "gs://bucket-1/memory.json",
        "memory.json",
    ]
    assert storage.list_objects("gs://bucket-1") == ["storage", "ls", "gs://bucket-1"]
    assert storage.delete_object("gs://bucket-1/memory.json") == ["storage", "rm", "gs://bucket-1/memory.json"]
    assert storage.grant_bucket_access("bucket-1", "serviceAccount:runner@example.test") == [
        "storage",
        "buckets",
        "add-iam-policy-binding",
        "gs://bucket-1",
        "--member=serviceAccount:runner@example.test",
        "--role=roles/storage.objectAdmin",
    ]


def test_logging_builders_emit_text_and_json_reads() -> None:
    spec = LogQuerySpec(
        filter_str='resource.type="cloud_run_job"',
        limit=25,
        order="asc",
        freshness="7d",
    )

    assert logging_.read_logs(spec) == [
        "logging",
        "read",
        'resource.type="cloud_run_job"',
        "--limit=25",
        "--freshness=7d",
        "--order=asc",
    ]
    assert logging_.read_logs_text(spec) == [
        "logging",
        "read",
        'resource.type="cloud_run_job"',
        "--limit=25",
        "--freshness=7d",
        "--order=asc",
        "--format=value(textPayload)",
    ]
    assert logging_.read_logs_json(spec) == [
        "logging",
        "read",
        'resource.type="cloud_run_job"',
        "--limit=25",
        "--freshness=7d",
        "--order=asc",
        "--format=json",
    ]
    assert logging_.job_log_filter("job-1") == 'resource.type="cloud_run_job" resource.labels.job_name="job-1"'
    assert logging_.job_log_filter("job-1", "execution-1") == (
        'resource.type="cloud_run_job" '
        'resource.labels.job_name="job-1" '
        'labels."run.googleapis.com/execution-name"="execution-1"'
    )
    assert logging_.tail_service_logs("service-1") == [
        "beta",
        "run",
        "services",
        "logs",
        "tail",
        "service-1",
    ]


def test_monitoring_builders_emit_expected_shapes() -> None:
    policy = AlertPolicySpec(
        display_name="job failure",
        metric_filter='resource.type="cloud_run_job"',
        notification_channels=["channels/123", "channels/456"],
        threshold_value=0.0,
        comparison="COMPARISON_GT",
    )

    assert monitoring.create_email_notification_channel("HarnessIQ Alerts", "ops@example.test") == [
        "monitoring",
        "channels",
        "create",
        "--display-name=HarnessIQ Alerts",
        "--type=email",
        "--channel-labels=email_address=ops@example.test",
        "--format=value(name)",
    ]
    assert monitoring.list_notification_channels() == [
        "monitoring",
        "channels",
        "list",
        "--format=json",
    ]
    assert monitoring.delete_notification_channel("channels/123") == [
        "monitoring",
        "channels",
        "delete",
        "channels/123",
        "--quiet",
    ]
    assert monitoring.create_alert_policy(policy) == [
        "alpha",
        "monitoring",
        "policies",
        "create",
        "--display-name=job failure",
        '--condition-filter=resource.type="cloud_run_job"',
        "--condition-threshold-value=0.0",
        "--condition-threshold-comparison=COMPARISON_GT",
        "--notification-channels=channels/123,channels/456",
        "--format=value(name)",
    ]
    assert monitoring.list_alert_policies() == ["alpha", "monitoring", "policies", "list", "--format=json"]
    assert monitoring.delete_alert_policy("policies/abc") == [
        "alpha",
        "monitoring",
        "policies",
        "delete",
        "policies/abc",
        "--quiet",
    ]
    assert monitoring.job_failure_filter("job-1") == (
        'resource.type="cloud_run_job" '
        'resource.labels.job_name="job-1" '
        'metric.type="run.googleapis.com/job/completed_execution_count" '
        'metric.labels.result="failed"'
    )


def test_commands_package_exports_support_surface() -> None:
    assert cmd.auth is auth
    assert cmd.iam is iam
    assert cmd.storage is storage
    assert cmd.logging is logging_
    assert cmd.monitoring is monitoring
    assert cmd.list_active_accounts is auth.list_active_accounts
    assert cmd.create_bucket is storage.create_bucket
    assert cmd.read_logs_json is logging_.read_logs_json
    assert cmd.create_alert_policy is monitoring.create_alert_policy


def test_support_builders_avoid_project_flags() -> None:
    commands = [
        auth.list_active_accounts(),
        iam.list_service_accounts(),
        storage.describe_bucket("bucket-1"),
        logging_.read_logs(LogQuerySpec(filter_str="severity>=ERROR")),
        monitoring.list_alert_policies(),
        logging_.tail_service_logs("service-1"),
    ]
    for command in commands:
        assert not any(part.startswith("--project=") for part in command)
