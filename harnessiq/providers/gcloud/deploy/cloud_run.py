"""Cloud Run Jobs provider backed by pure gcloud command builders."""

from __future__ import annotations

from typing import Any

from harnessiq.providers.gcloud import commands as cmd
from harnessiq.providers.gcloud.base import BaseGcpProvider
from harnessiq.providers.gcloud.client import GcloudError


class CloudRunProvider(BaseGcpProvider):
    """Manage the Cloud Run Job lifecycle for one agent deployment."""

    def job_exists(self) -> bool:
        try:
            self.client.run_json(cmd.describe_job(self.config.job_name, self.config.region))
            return True
        except GcloudError:
            return False

    def create_job(self) -> str:
        return self.client.run(cmd.create_job(cmd.JobSpec.from_config(self.config)))

    def update_job(self) -> str:
        return self.client.run(cmd.update_job(cmd.JobSpec.from_config(self.config)))

    def deploy_job(self) -> str:
        if self.job_exists():
            return self.update_job()
        return self.create_job()

    def update_image(self, image_url: str) -> str:
        return self.client.run(
            cmd.update_job_image(self.config.job_name, self.config.region, image_url)
        )

    def execute(
        self,
        *,
        wait: bool = False,
        async_: bool = False,
        task_count: int | None = None,
        timeout_override: int | None = None,
        env_overrides: dict[str, str] | None = None,
    ) -> str:
        options = cmd.ExecutionOptions(
            wait=wait,
            async_=async_,
            task_count=task_count,
            timeout_override=timeout_override,
            env_overrides=dict(env_overrides or {}),
        )
        return self.client.run(
            cmd.execute_job(self.config.job_name, self.config.region, options)
        )

    def describe(self) -> dict[str, Any]:
        return self.client.run_json(
            cmd.describe_job(self.config.job_name, self.config.region)
        )

    def list_executions(self, limit: int = 10) -> list[dict[str, Any]]:
        return self.client.run_json(
            cmd.list_executions(self.config.job_name, self.config.region, limit)
        )

    def cancel_execution(self, execution_name: str) -> str:
        return self.client.run(
            cmd.cancel_execution(execution_name, self.config.region)
        )

    def delete(self) -> str:
        return self.client.run(cmd.delete_job(self.config.job_name, self.config.region))
