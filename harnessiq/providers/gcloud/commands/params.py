"""Typed parameter objects for pure GCP command builders."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SecretRef:
    """A Secret Manager secret injected into runtime as one environment variable."""

    env_var: str
    secret_name: str
    version: str = "latest"


@dataclass(slots=True)
class JobSpec:
    """Complete Cloud Run Job parameters shared across create and update commands."""

    job_name: str
    image_url: str
    region: str
    cpu: str = "1"
    memory: str = "512Mi"
    task_timeout_seconds: int = 3600
    max_retries: int = 1
    parallelism: int = 0
    task_count: int = 1
    env_vars: dict[str, str] = field(default_factory=dict)
    secrets: list[SecretRef] = field(default_factory=list)
    service_account_email: str = ""

    @classmethod
    def from_config(cls, config: Any) -> "JobSpec":
        """Derive a job command spec from a persisted GCP agent config."""
        return cls(
            job_name=config.job_name,
            image_url=config.image_url,
            region=config.region,
            cpu=config.cpu,
            memory=config.memory,
            task_timeout_seconds=config.task_timeout_seconds,
            max_retries=config.max_retries,
            parallelism=config.parallelism,
            task_count=config.task_count,
            env_vars=dict(config.env_vars),
            secrets=[
                SecretRef(env_var=entry["env_var"], secret_name=entry["secret_name"])
                for entry in config.secrets
            ],
            service_account_email=config.service_account_email or "",
        )


@dataclass(slots=True)
class ExecutionOptions:
    """Execution-time overrides for one immediate Cloud Run Job invocation."""

    wait: bool = False
    async_: bool = False
    task_count: int | None = None
    timeout_override: int | None = None
    env_overrides: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ScheduleSpec:
    """Parameters for a Cloud Scheduler job that triggers a Cloud Run Job."""

    scheduler_job_name: str
    location: str
    cron_expression: str
    http_uri: str
    service_account_email: str
    timezone: str = "UTC"
    description: str = ""


@dataclass(slots=True)
class SecretSpec:
    """Parameters for a Secret Manager secret lifecycle command."""

    secret_name: str
    project_id: str
    replication: str = "automatic"


@dataclass(slots=True)
class ServiceAccountSpec:
    """Parameters for creating one service account."""

    sa_id: str
    project_id: str
    display_name: str = ""
    description: str = ""


@dataclass(slots=True)
class IamBinding:
    """A project IAM binding granting one member one role."""

    project_id: str
    member: str
    role: str


@dataclass(slots=True)
class BucketSpec:
    """Parameters for a GCS bucket creation command."""

    bucket_name: str
    location: str
    uniform_access: bool = True


@dataclass(slots=True)
class LogQuerySpec:
    """Parameters for Cloud Logging query builders."""

    filter_str: str
    limit: int = 100
    order: str = "desc"
    freshness: str | None = None


@dataclass(slots=True)
class AlertPolicySpec:
    """Parameters for a Cloud Monitoring alerting policy builder."""

    display_name: str
    metric_filter: str
    notification_channels: list[str]
    threshold_value: float = 0.0
    comparison: str = "COMPARISON_GT"
    duration_seconds: int = 0
    alignment_period_seconds: int = 60
