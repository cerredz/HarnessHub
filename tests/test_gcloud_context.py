from harnessiq.providers.gcloud import (
    ArtifactRegistryProvider,
    BillingProvider,
    CloudRunProvider,
    CloudStorageProvider,
    GcpAgentConfig,
    GcpContext,
    HealthProvider,
    LoggingProvider,
    MonitoringProvider,
    SchedulerProvider,
    SecretManagerProvider,
)


def test_context_composes_namespaces_with_shared_client_and_config() -> None:
    config = GcpAgentConfig(
        agent_name="candidate-a",
        gcp_project_id="proj-123",
        region="us-central1",
        service_account_email="runner@proj-123.iam.gserviceaccount.com",
    )
    context = GcpContext.from_init(
        agent_name=config.agent_name,
        project_id=config.gcp_project_id,
        region=config.region,
        service_account_email=config.service_account_email,
    )

    assert isinstance(context.health, HealthProvider)
    assert isinstance(context.infra.billing, BillingProvider)
    assert isinstance(context.deploy.artifact_registry, ArtifactRegistryProvider)
    assert isinstance(context.deploy.cloud_run, CloudRunProvider)
    assert isinstance(context.deploy.scheduler, SchedulerProvider)
    assert isinstance(context.credentials.secret_manager, SecretManagerProvider)
    assert isinstance(context.storage, CloudStorageProvider)
    assert isinstance(context.observability.logging, LoggingProvider)
    assert isinstance(context.observability.monitoring, MonitoringProvider)

    providers = [
        context.health,
        context.infra.billing,
        context.infra.iam,
        context.deploy.artifact_registry,
        context.deploy.cloud_run,
        context.deploy.scheduler,
        context.credentials.secret_manager,
        context.storage,
        context.observability.logging,
        context.observability.monitoring,
    ]
    assert all(provider.client is context.client for provider in providers)
    assert all(provider.config is context.config for provider in providers)


def test_context_from_config_loads_saved_config(monkeypatch) -> None:
    config = GcpAgentConfig(
        agent_name="candidate-a",
        gcp_project_id="proj-123",
        region="us-central1",
    )
    monkeypatch.setattr(GcpAgentConfig, "load", classmethod(lambda cls, agent_name: config))

    context = GcpContext.from_config("candidate-a", dry_run=True)

    assert context.config is config
    assert context.client.project_id == "proj-123"
    assert context.client.region == "us-central1"
    assert context.client.dry_run is True


def test_context_from_init_constructs_unsaved_config() -> None:
    context = GcpContext.from_init(
        agent_name="candidate-a",
        project_id="proj-123",
        region="us-central1",
        schedule_cron="0 */4 * * *",
    )

    assert context.config.agent_name == "candidate-a"
    assert context.config.gcp_project_id == "proj-123"
    assert context.config.region == "us-central1"
    assert context.config.schedule_cron == "0 */4 * * *"
    assert context.client.project_id == "proj-123"
