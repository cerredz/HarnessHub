"""Shared composition root for GCP-backed HarnessIQ provider operations."""

from __future__ import annotations

from dataclasses import dataclass

from harnessiq.providers.gcloud.client import GcloudClient
from harnessiq.providers.gcloud.config import GcpAgentConfig
from harnessiq.providers.gcloud.credentials import SecretManagerProvider
from harnessiq.providers.gcloud.deploy import (
    ArtifactRegistryProvider,
    CloudRunProvider,
    SchedulerProvider,
)
from harnessiq.providers.gcloud.health import HealthProvider
from harnessiq.providers.gcloud.infra import BillingProvider, IamProvider
from harnessiq.providers.gcloud.observability import LoggingProvider, MonitoringProvider
from harnessiq.providers.gcloud.storage import CloudStorageProvider


@dataclass(slots=True)
class DeployProviders:
    """Deployment-oriented providers grouped under one namespace."""

    artifact_registry: ArtifactRegistryProvider
    cloud_run: CloudRunProvider
    scheduler: SchedulerProvider


@dataclass(slots=True)
class InfraProviders:
    """Infrastructure-oriented providers grouped under one namespace."""

    iam: IamProvider
    billing: BillingProvider


@dataclass(slots=True)
class CredentialProviders:
    """Credential-related providers grouped under one namespace."""

    secret_manager: SecretManagerProvider


@dataclass(slots=True)
class ObservabilityProviders:
    """Observability providers grouped under one namespace."""

    logging: LoggingProvider
    monitoring: MonitoringProvider


class GcpContext:
    """Single entry point for all GCP provider operations on one agent config."""

    def __init__(self, client: GcloudClient, config: GcpAgentConfig) -> None:
        self._client = client
        self._config = config

        self.health = HealthProvider(client, config)
        self.infra = InfraProviders(
            iam=IamProvider(client, config),
            billing=BillingProvider(client, config),
        )
        self.deploy = DeployProviders(
            artifact_registry=ArtifactRegistryProvider(client, config),
            cloud_run=CloudRunProvider(client, config),
            scheduler=SchedulerProvider(client, config),
        )
        self.credentials = CredentialProviders(
            secret_manager=SecretManagerProvider(client, config),
        )
        self.storage = CloudStorageProvider(client, config)
        self.observability = ObservabilityProviders(
            logging=LoggingProvider(client, config),
            monitoring=MonitoringProvider(client, config),
        )

    @property
    def client(self) -> GcloudClient:
        return self._client

    @property
    def config(self) -> GcpAgentConfig:
        return self._config

    @classmethod
    def from_config(cls, agent_name: str, dry_run: bool = False) -> "GcpContext":
        config = GcpAgentConfig.load(agent_name)
        client = GcloudClient(
            project_id=config.gcp_project_id,
            region=config.region,
            dry_run=dry_run,
        )
        return cls(client, config)

    @classmethod
    def from_init(
        cls,
        agent_name: str,
        project_id: str,
        region: str,
        **kwargs,
    ) -> "GcpContext":
        config = GcpAgentConfig(
            agent_name=agent_name,
            gcp_project_id=project_id,
            region=region,
            **kwargs,
        )
        client = GcloudClient(project_id=project_id, region=region)
        return cls(client, config)
