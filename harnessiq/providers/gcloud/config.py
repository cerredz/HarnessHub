"""Persisted configuration for one GCP-backed HarnessIQ deployment."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from harnessiq.config import build_harness_credential_binding_name
from harnessiq.utils.ledger_connections import harnessiq_home_dir

DEFAULT_GCP_CONFIG_DIRNAME = "gcloud"
DEFAULT_ARTIFACT_REPOSITORY_NAME = "harnessiq"
DEFAULT_IMAGE_TAG = "latest"
DEFAULT_CPU = "1"
DEFAULT_MEMORY = "512Mi"
DEFAULT_TASK_TIMEOUT_SECONDS = 3600
DEFAULT_MAX_RETRIES = 1
DEFAULT_PARALLELISM = 0
DEFAULT_TASK_COUNT = 1
DEFAULT_TIMEZONE = "UTC"


@dataclass(slots=True)
class GcpAgentConfig:
    """Persisted deploy configuration for one logical HarnessIQ agent."""

    agent_name: str
    gcp_project_id: str
    region: str
    artifact_repository: str = DEFAULT_ARTIFACT_REPOSITORY_NAME
    image_name: str = ""
    image_tag: str = DEFAULT_IMAGE_TAG
    job_name: str = ""
    scheduler_job_name: str = ""
    service_account_email: str | None = None
    cpu: str = DEFAULT_CPU
    memory: str = DEFAULT_MEMORY
    task_timeout_seconds: int = DEFAULT_TASK_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES
    parallelism: int = DEFAULT_PARALLELISM
    task_count: int = DEFAULT_TASK_COUNT
    env_vars: dict[str, str] = field(default_factory=dict)
    secrets: list[dict[str, str]] = field(default_factory=list)
    schedule_cron: str | None = None
    timezone: str = DEFAULT_TIMEZONE
    manifest_id: str | None = None
    model: str | None = None
    model_profile: str | None = None
    model_factory: str | None = None
    sink_specs: list[str] = field(default_factory=list)
    adapter_arguments: dict[str, Any] = field(default_factory=dict)
    runtime_parameters: dict[str, Any] = field(default_factory=dict)
    custom_parameters: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.agent_name = self.agent_name.strip()
        self.gcp_project_id = self.gcp_project_id.strip()
        self.region = self.region.strip()
        self.artifact_repository = self.artifact_repository.strip()
        self.image_name = (self.image_name or self._default_image_name()).strip()
        self.image_tag = self.image_tag.strip()
        self.job_name = (self.job_name or self._default_job_name()).strip()
        self.scheduler_job_name = (self.scheduler_job_name or self._default_scheduler_job_name()).strip()
        self.service_account_email = self._normalize_optional_string(self.service_account_email)
        self.cpu = self.cpu.strip()
        self.memory = self.memory.strip()
        self.schedule_cron = self._normalize_optional_string(self.schedule_cron)
        self.timezone = self.timezone.strip()
        self.manifest_id = self._normalize_optional_string(self.manifest_id)
        self.model = self._normalize_optional_string(self.model)
        self.model_profile = self._normalize_optional_string(self.model_profile)
        self.model_factory = self._normalize_optional_string(self.model_factory)
        self.env_vars = {str(key): str(value) for key, value in self.env_vars.items()}
        self.secrets = [self._normalize_secret_entry(item) for item in self.secrets]
        self.sink_specs = [str(item) for item in self.sink_specs]
        self.adapter_arguments = dict(self.adapter_arguments)
        self.runtime_parameters = dict(self.runtime_parameters)
        self.custom_parameters = dict(self.custom_parameters)

        if not self.agent_name:
            raise ValueError("agent_name must not be blank.")
        if not self.gcp_project_id:
            raise ValueError("gcp_project_id must not be blank.")
        if not self.region:
            raise ValueError("region must not be blank.")
        if not self.artifact_repository:
            raise ValueError("artifact_repository must not be blank.")
        if not self.image_name:
            raise ValueError("image_name must not be blank.")
        if not self.image_tag:
            raise ValueError("image_tag must not be blank.")
        if not self.job_name:
            raise ValueError("job_name must not be blank.")
        if not self.scheduler_job_name:
            raise ValueError("scheduler_job_name must not be blank.")
        if not self.cpu:
            raise ValueError("cpu must not be blank.")
        if not self.memory:
            raise ValueError("memory must not be blank.")
        if not self.timezone:
            raise ValueError("timezone must not be blank.")
        if self.task_timeout_seconds <= 0:
            raise ValueError("task_timeout_seconds must be greater than zero.")
        if self.max_retries < 0:
            raise ValueError("max_retries must be greater than or equal to zero.")
        if self.parallelism < 0:
            raise ValueError("parallelism must be greater than or equal to zero.")
        if self.task_count <= 0:
            raise ValueError("task_count must be greater than zero.")

    @property
    def image_url(self) -> str:
        """Return the Artifact Registry image URL for this config."""
        return (
            f"{self.region}-docker.pkg.dev/"
            f"{self.gcp_project_id}/"
            f"{self.artifact_repository}/"
            f"{self.image_name}:{self.image_tag}"
        )

    @property
    def credential_binding_name(self) -> str:
        """Return the repo-local harness credential-binding key for this config."""
        if self.manifest_id is None:
            raise ValueError("manifest_id must be set to resolve a harness credential binding.")
        return build_harness_credential_binding_name(
            manifest_id=self.manifest_id,
            agent_name=self.agent_name,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "adapter_arguments": dict(self.adapter_arguments),
            "agent_name": self.agent_name,
            "artifact_repository": self.artifact_repository,
            "cpu": self.cpu,
            "custom_parameters": dict(self.custom_parameters),
            "env_vars": dict(self.env_vars),
            "gcp_project_id": self.gcp_project_id,
            "image_name": self.image_name,
            "image_tag": self.image_tag,
            "job_name": self.job_name,
            "manifest_id": self.manifest_id,
            "max_retries": self.max_retries,
            "memory": self.memory,
            "model": self.model,
            "model_factory": self.model_factory,
            "model_profile": self.model_profile,
            "parallelism": self.parallelism,
            "region": self.region,
            "runtime_parameters": dict(self.runtime_parameters),
            "schedule_cron": self.schedule_cron,
            "scheduler_job_name": self.scheduler_job_name,
            "secrets": list(self.secrets),
            "service_account_email": self.service_account_email,
            "sink_specs": list(self.sink_specs),
            "task_count": self.task_count,
            "task_timeout_seconds": self.task_timeout_seconds,
            "timezone": self.timezone,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "GcpAgentConfig":
        return cls(
            adapter_arguments=dict(payload.get("adapter_arguments", {})),
            agent_name=str(payload["agent_name"]),
            artifact_repository=str(payload.get("artifact_repository", DEFAULT_ARTIFACT_REPOSITORY_NAME)),
            cpu=str(payload.get("cpu", DEFAULT_CPU)),
            custom_parameters=dict(payload.get("custom_parameters", {})),
            env_vars=dict(payload.get("env_vars", {})),
            gcp_project_id=str(payload["gcp_project_id"]),
            image_name=str(payload.get("image_name", "")),
            image_tag=str(payload.get("image_tag", DEFAULT_IMAGE_TAG)),
            job_name=str(payload.get("job_name", "")),
            manifest_id=(str(payload["manifest_id"]) if payload.get("manifest_id") is not None else None),
            max_retries=int(payload.get("max_retries", DEFAULT_MAX_RETRIES)),
            memory=str(payload.get("memory", DEFAULT_MEMORY)),
            model=(str(payload["model"]) if payload.get("model") is not None else None),
            model_factory=(str(payload["model_factory"]) if payload.get("model_factory") is not None else None),
            model_profile=(str(payload["model_profile"]) if payload.get("model_profile") is not None else None),
            parallelism=int(payload.get("parallelism", DEFAULT_PARALLELISM)),
            region=str(payload["region"]),
            runtime_parameters=dict(payload.get("runtime_parameters", {})),
            schedule_cron=(str(payload["schedule_cron"]) if payload.get("schedule_cron") is not None else None),
            scheduler_job_name=str(payload.get("scheduler_job_name", "")),
            secrets=list(payload.get("secrets", [])),
            service_account_email=(
                str(payload["service_account_email"])
                if payload.get("service_account_email") is not None
                else None
            ),
            sink_specs=list(payload.get("sink_specs", [])),
            task_count=int(payload.get("task_count", DEFAULT_TASK_COUNT)),
            task_timeout_seconds=int(payload.get("task_timeout_seconds", DEFAULT_TASK_TIMEOUT_SECONDS)),
            timezone=str(payload.get("timezone", DEFAULT_TIMEZONE)),
        )

    @classmethod
    def config_dir(cls, home_dir: Path | str | None = None) -> Path:
        return harnessiq_home_dir(home_dir) / DEFAULT_GCP_CONFIG_DIRNAME

    @classmethod
    def config_path_for(cls, agent_name: str, home_dir: Path | str | None = None) -> Path:
        normalized_name = agent_name.strip()
        if not normalized_name:
            raise ValueError("agent_name must not be blank.")
        return cls.config_dir(home_dir) / f"{normalized_name}.json"

    @classmethod
    def load(cls, agent_name: str, home_dir: Path | str | None = None) -> "GcpAgentConfig":
        path = cls.config_path_for(agent_name, home_dir)
        if not path.exists():
            raise FileNotFoundError(f"No GCP config exists for agent '{agent_name}' at '{path}'.")
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            raise ValueError(f"GCP config file '{path}' is empty.")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("GCP config file must contain a JSON object.")
        config = cls.from_dict(payload)
        if config.agent_name != agent_name.strip():
            raise ValueError(
                f"GCP config '{path}' belongs to agent '{config.agent_name}', not '{agent_name.strip()}'."
            )
        return config

    def save(self, home_dir: Path | str | None = None) -> Path:
        path = self.config_path_for(self.agent_name, home_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.as_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return path

    def _default_image_name(self) -> str:
        return self._slug(self.agent_name)

    def _default_job_name(self) -> str:
        return f"harnessiq-{self._slug(self.agent_name)}"

    def _default_scheduler_job_name(self) -> str:
        return f"{self.job_name or self._default_job_name()}-schedule"

    @staticmethod
    def _normalize_optional_string(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _normalize_secret_entry(payload: Mapping[str, Any]) -> dict[str, str]:
        secret_name = str(payload["secret_name"]).strip()
        env_var = str(payload["env_var"]).strip()
        if not secret_name:
            raise ValueError("secret_name must not be blank.")
        if not env_var:
            raise ValueError("env_var must not be blank.")
        return {
            "env_var": env_var,
            "secret_name": secret_name,
        }

    @staticmethod
    def _slug(value: str) -> str:
        lowered = value.strip().lower()
        slug = "".join(character if character.isalnum() else "-" for character in lowered)
        compact = "-".join(part for part in slug.split("-") if part)
        return compact or "agent"
