from harnessiq.providers.gcloud import commands as cmd
from harnessiq.providers.gcloud.commands import artifact_registry, run_jobs, scheduler, secret_manager
from harnessiq.providers.gcloud.commands.params import ExecutionOptions, JobSpec, ScheduleSpec, SecretRef, SecretSpec


def _job_spec(**overrides) -> JobSpec:
    defaults = {
        "job_name": "candidate-a",
        "image_url": "us-central1-docker.pkg.dev/proj-123/harnessiq/candidate-a:latest",
        "region": "us-central1",
    }
    return JobSpec(**(defaults | overrides))


def test_cloud_run_create_and_update_share_capacity_flags() -> None:
    spec = _job_spec(
        cpu="2",
        memory="1Gi",
        task_timeout_seconds=7200,
        max_retries=4,
        task_count=3,
        parallelism=5,
        env_vars={"FOO": "bar"},
        secrets=[SecretRef("ANTHROPIC_API_KEY", "HARNESSIQ_ANTHROPIC_API_KEY")],
        service_account_email="runner@proj-123.iam.gserviceaccount.com",
    )

    create = run_jobs.create_job(spec)
    update = run_jobs.update_job(spec)

    for flag in [
        "--image=us-central1-docker.pkg.dev/proj-123/harnessiq/candidate-a:latest",
        "--region=us-central1",
        "--cpu=2",
        "--memory=1Gi",
        "--task-timeout=7200s",
        "--max-retries=4",
        "--tasks=3",
        "--parallelism=5",
        "--set-env-vars=FOO=bar",
        "--set-secrets=ANTHROPIC_API_KEY=HARNESSIQ_ANTHROPIC_API_KEY:latest",
        "--service-account=runner@proj-123.iam.gserviceaccount.com",
    ]:
        assert flag in create
        assert flag in update

    assert create[:4] == ["run", "jobs", "create", "candidate-a"]
    assert update[:4] == ["run", "jobs", "update", "candidate-a"]


def test_cloud_run_job_update_helpers_emit_expected_shapes() -> None:
    assert run_jobs.update_job_env("candidate-a", "us-central1", add={"FOO": "bar"}) == [
        "run",
        "jobs",
        "update",
        "candidate-a",
        "--region=us-central1",
        "--update-env-vars=FOO=bar",
    ]
    assert run_jobs.update_job_env("candidate-a", "us-central1", remove=["FOO", "BAR"]) == [
        "run",
        "jobs",
        "update",
        "candidate-a",
        "--region=us-central1",
        "--remove-env-vars=FOO,BAR",
    ]
    assert run_jobs.update_job_secrets(
        "candidate-a",
        "us-central1",
        add=[SecretRef("ANTHROPIC_API_KEY", "HARNESSIQ_ANTHROPIC_API_KEY")],
        remove=["LINKEDIN_PASSWORD"],
    ) == [
        "run",
        "jobs",
        "update",
        "candidate-a",
        "--region=us-central1",
        "--set-secrets=ANTHROPIC_API_KEY=HARNESSIQ_ANTHROPIC_API_KEY:latest",
        "--remove-secrets=LINKEDIN_PASSWORD",
    ]
    assert run_jobs.update_job_image(
        "candidate-a",
        "us-central1",
        "us-central1-docker.pkg.dev/proj/repo/image:sha",
    ) == [
        "run",
        "jobs",
        "update",
        "candidate-a",
        "--region=us-central1",
        "--image=us-central1-docker.pkg.dev/proj/repo/image:sha",
    ]


def test_cloud_run_execute_and_read_commands() -> None:
    opts = ExecutionOptions(wait=True, task_count=3, timeout_override=900, env_overrides={"FOO": "bar"})
    assert run_jobs.execute_job("candidate-a", "us-central1", opts) == [
        "run",
        "jobs",
        "execute",
        "candidate-a",
        "--region=us-central1",
        "--wait",
        "--tasks=3",
        "--task-timeout=900s",
        "--update-env-vars=FOO=bar",
    ]
    assert run_jobs.execute_job("candidate-a", "us-central1", ExecutionOptions(async_=True)) == [
        "run",
        "jobs",
        "execute",
        "candidate-a",
        "--region=us-central1",
        "--async",
    ]
    assert run_jobs.describe_job("candidate-a", "us-central1") == [
        "run",
        "jobs",
        "describe",
        "candidate-a",
        "--region=us-central1",
        "--format=json",
    ]
    assert run_jobs.list_jobs("us-central1") == [
        "run",
        "jobs",
        "list",
        "--region=us-central1",
        "--format=json",
    ]
    assert run_jobs.delete_job("candidate-a", "us-central1") == [
        "run",
        "jobs",
        "delete",
        "candidate-a",
        "--region=us-central1",
        "--quiet",
    ]
    assert run_jobs.list_executions("candidate-a", "us-central1", limit=2) == [
        "run",
        "jobs",
        "executions",
        "list",
        "--filter=job:candidate-a",
        "--region=us-central1",
        "--limit=2",
        "--format=json",
    ]
    assert run_jobs.describe_execution("candidate-a-001", "us-central1") == [
        "run",
        "jobs",
        "executions",
        "describe",
        "candidate-a-001",
        "--region=us-central1",
        "--format=json",
    ]
    assert run_jobs.cancel_execution("candidate-a-001", "us-central1") == [
        "run",
        "jobs",
        "executions",
        "cancel",
        "candidate-a-001",
        "--region=us-central1",
        "--quiet",
    ]
    assert run_jobs.delete_execution("candidate-a-001", "us-central1") == [
        "run",
        "jobs",
        "executions",
        "delete",
        "candidate-a-001",
        "--region=us-central1",
        "--quiet",
    ]
    assert run_jobs.get_latest_execution_name("candidate-a", "us-central1") == [
        "run",
        "jobs",
        "executions",
        "list",
        "--filter=job:candidate-a",
        "--region=us-central1",
        "--limit=1",
        "--format=value(name)",
    ]


def test_scheduler_builders_emit_expected_commands() -> None:
    spec = ScheduleSpec(
        scheduler_job_name="candidate-a-schedule",
        location="us-central1",
        cron_expression="0 */4 * * *",
        http_uri="https://run.googleapis.com/v2/projects/proj/locations/us-central1/jobs/candidate-a:run",
        service_account_email="runner@proj-123.iam.gserviceaccount.com",
        description="Runs candidate-a",
    )
    assert scheduler.create_schedule(spec) == [
        "scheduler",
        "jobs",
        "create",
        "http",
        "candidate-a-schedule",
        "--location=us-central1",
        "--schedule=0 */4 * * *",
        "--time-zone=UTC",
        "--uri=https://run.googleapis.com/v2/projects/proj/locations/us-central1/jobs/candidate-a:run",
        "--http-method=POST",
        "--oauth-service-account-email=runner@proj-123.iam.gserviceaccount.com",
        "--message-body={}",
        "--description=Runs candidate-a",
    ]
    assert scheduler.update_schedule("candidate-a-schedule", "us-central1", cron="0 0 * * *") == [
        "scheduler",
        "jobs",
        "update",
        "http",
        "candidate-a-schedule",
        "--location=us-central1",
        "--schedule=0 0 * * *",
    ]
    assert scheduler.describe_schedule("candidate-a-schedule", "us-central1") == [
        "scheduler",
        "jobs",
        "describe",
        "candidate-a-schedule",
        "--location=us-central1",
        "--format=json",
    ]
    assert scheduler.list_schedules("us-central1") == [
        "scheduler",
        "jobs",
        "list",
        "--location=us-central1",
        "--format=json",
    ]
    assert scheduler.delete_schedule("candidate-a-schedule", "us-central1") == [
        "scheduler",
        "jobs",
        "delete",
        "candidate-a-schedule",
        "--location=us-central1",
        "--quiet",
    ]
    assert scheduler.pause_schedule("candidate-a-schedule", "us-central1") == [
        "scheduler",
        "jobs",
        "pause",
        "candidate-a-schedule",
        "--location=us-central1",
    ]
    assert scheduler.resume_schedule("candidate-a-schedule", "us-central1") == [
        "scheduler",
        "jobs",
        "resume",
        "candidate-a-schedule",
        "--location=us-central1",
    ]
    assert scheduler.run_schedule_now("candidate-a-schedule", "us-central1") == [
        "scheduler",
        "jobs",
        "run",
        "candidate-a-schedule",
        "--location=us-central1",
    ]


def test_artifact_registry_builders_emit_expected_commands() -> None:
    assert artifact_registry.create_repository("harnessiq", "us-central1") == [
        "artifacts",
        "repositories",
        "create",
        "harnessiq",
        "--repository-format=docker",
        "--location=us-central1",
        "--quiet",
    ]
    assert artifact_registry.describe_repository("harnessiq", "us-central1") == [
        "artifacts",
        "repositories",
        "describe",
        "harnessiq",
        "--location=us-central1",
        "--format=json",
    ]
    assert artifact_registry.list_repositories("us-central1") == [
        "artifacts",
        "repositories",
        "list",
        "--location=us-central1",
        "--format=json",
    ]
    assert artifact_registry.delete_repository("harnessiq", "us-central1") == [
        "artifacts",
        "repositories",
        "delete",
        "harnessiq",
        "--location=us-central1",
        "--quiet",
    ]
    assert artifact_registry.configure_docker_auth("us-central1") == [
        "auth",
        "configure-docker",
        "us-central1-docker.pkg.dev",
        "--quiet",
    ]
    assert artifact_registry.submit_build("us-central1-docker.pkg.dev/proj/repo/image:latest") == [
        "builds",
        "submit",
        "--tag=us-central1-docker.pkg.dev/proj/repo/image:latest",
        ".",
    ]
    assert artifact_registry.list_images("us-central1-docker.pkg.dev/proj/repo", "us-central1") == [
        "artifacts",
        "docker",
        "images",
        "list",
        "us-central1-docker.pkg.dev/proj/repo",
        "--location=us-central1",
        "--format=json",
    ]
    assert artifact_registry.delete_image("us-central1-docker.pkg.dev/proj/repo/image:latest") == [
        "artifacts",
        "docker",
        "images",
        "delete",
        "us-central1-docker.pkg.dev/proj/repo/image:latest",
        "--delete-tags",
        "--quiet",
    ]


def test_secret_manager_builders_emit_expected_commands() -> None:
    spec = SecretSpec(secret_name="HARNESSIQ_ANTHROPIC_API_KEY", project_id="proj-123")
    assert secret_manager.create_secret(spec) == [
        "secrets",
        "create",
        "HARNESSIQ_ANTHROPIC_API_KEY",
        "--replication-policy=automatic",
    ]
    assert secret_manager.add_secret_version("HARNESSIQ_ANTHROPIC_API_KEY") == [
        "secrets",
        "versions",
        "add",
        "HARNESSIQ_ANTHROPIC_API_KEY",
        "--data-file=-",
    ]
    assert secret_manager.access_secret_version("HARNESSIQ_ANTHROPIC_API_KEY") == [
        "secrets",
        "versions",
        "access",
        "latest",
        "--secret=HARNESSIQ_ANTHROPIC_API_KEY",
    ]
    assert secret_manager.describe_secret("HARNESSIQ_ANTHROPIC_API_KEY") == [
        "secrets",
        "describe",
        "HARNESSIQ_ANTHROPIC_API_KEY",
        "--format=json",
    ]
    assert secret_manager.list_secrets() == ["secrets", "list", "--format=json"]
    assert secret_manager.list_secret_versions("HARNESSIQ_ANTHROPIC_API_KEY") == [
        "secrets",
        "versions",
        "list",
        "HARNESSIQ_ANTHROPIC_API_KEY",
        "--format=json",
    ]
    assert secret_manager.delete_secret("HARNESSIQ_ANTHROPIC_API_KEY") == [
        "secrets",
        "delete",
        "HARNESSIQ_ANTHROPIC_API_KEY",
        "--quiet",
    ]
    assert secret_manager.grant_secret_access(
        "HARNESSIQ_ANTHROPIC_API_KEY",
        "serviceAccount:runner@example.test",
    ) == [
        "secrets",
        "add-iam-policy-binding",
        "HARNESSIQ_ANTHROPIC_API_KEY",
        "--member=serviceAccount:runner@example.test",
        "--role=roles/secretmanager.secretAccessor",
    ]
    assert secret_manager.revoke_secret_access(
        "HARNESSIQ_ANTHROPIC_API_KEY",
        "serviceAccount:runner@example.test",
    ) == [
        "secrets",
        "remove-iam-policy-binding",
        "HARNESSIQ_ANTHROPIC_API_KEY",
        "--member=serviceAccount:runner@example.test",
        "--role=roles/secretmanager.secretAccessor",
    ]
    assert secret_manager.enable_secret_manager_api() == [
        "services",
        "enable",
        "secretmanager.googleapis.com",
    ]


def test_commands_package_exports_deploy_surface() -> None:
    assert cmd.run_jobs is run_jobs
    assert cmd.scheduler is scheduler
    assert cmd.artifact_registry is artifact_registry
    assert cmd.secret_manager is secret_manager
    assert cmd.create_job is run_jobs.create_job
    assert cmd.create_schedule is scheduler.create_schedule
    assert cmd.create_repository is artifact_registry.create_repository
    assert cmd.create_secret is secret_manager.create_secret


def test_deploy_builders_avoid_project_flags() -> None:
    commands = [
        run_jobs.describe_job("candidate-a", "us-central1"),
        scheduler.list_schedules("us-central1"),
        artifact_registry.list_repositories("us-central1"),
        secret_manager.describe_secret("HARNESSIQ_ANTHROPIC_API_KEY"),
    ]
    for command in commands:
        assert not any(part.startswith("--project=") for part in command)
