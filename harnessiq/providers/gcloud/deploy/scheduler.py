"""Cloud Scheduler provider backed by pure gcloud command builders."""

from __future__ import annotations

from typing import Any

from harnessiq.providers.gcloud import commands as cmd
from harnessiq.providers.gcloud.base import BaseGcpProvider
from harnessiq.providers.gcloud.client import GcloudError


class SchedulerProvider(BaseGcpProvider):
    """Manage the scheduler job that triggers one Cloud Run job."""

    @property
    def job_uri(self) -> str:
        return (
            "https://run.googleapis.com/v2/projects/"
            f"{self.config.gcp_project_id}/locations/"
            f"{self.config.region}/jobs/{self.config.job_name}:run"
        )

    def schedule_exists(self) -> bool:
        try:
            self.client.run_json(
                cmd.describe_schedule(self.config.scheduler_job_name, self.config.region)
            )
            return True
        except GcloudError as exc:
            if self._is_not_found_error(exc):
                return False
            raise

    def create_schedule(
        self,
        *,
        service_account_email: str | None = None,
        cron: str | None = None,
        timezone: str | None = None,
        description: str = "",
    ) -> str:
        spec = self._schedule_spec(
            service_account_email=service_account_email,
            cron=cron,
            timezone=timezone,
            description=description,
        )
        return self.client.run(cmd.create_schedule(spec))

    def update_schedule(
        self,
        *,
        cron: str | None = None,
        timezone: str | None = None,
    ) -> str:
        return self.client.run(
            cmd.update_schedule(
                self.config.scheduler_job_name,
                self.config.region,
                cron=cron,
                timezone=timezone,
            )
        )

    def deploy_schedule(
        self,
        *,
        service_account_email: str | None = None,
        cron: str | None = None,
        timezone: str | None = None,
        description: str = "",
    ) -> str:
        if self.schedule_exists():
            return self.update_schedule(cron=cron, timezone=timezone)
        return self.create_schedule(
            service_account_email=service_account_email,
            cron=cron,
            timezone=timezone,
            description=description,
        )

    def describe(self) -> dict[str, Any]:
        return self.client.run_json(
            cmd.describe_schedule(self.config.scheduler_job_name, self.config.region)
        )

    def list_schedules(self) -> list[dict[str, Any]]:
        return self.client.run_json(cmd.list_schedules(self.config.region))

    def pause(self) -> str:
        return self.client.run(
            cmd.pause_schedule(self.config.scheduler_job_name, self.config.region)
        )

    def resume(self) -> str:
        return self.client.run(
            cmd.resume_schedule(self.config.scheduler_job_name, self.config.region)
        )

    def run_now(self) -> str:
        return self.client.run(
            cmd.run_schedule_now(self.config.scheduler_job_name, self.config.region)
        )

    def delete(self) -> str:
        return self.client.run(
            cmd.delete_schedule(self.config.scheduler_job_name, self.config.region)
        )

    def _schedule_spec(
        self,
        *,
        service_account_email: str | None,
        cron: str | None,
        timezone: str | None,
        description: str,
    ) -> cmd.ScheduleSpec:
        resolved_service_account = (service_account_email or self.config.service_account_email or "").strip()
        if not resolved_service_account:
            raise ValueError(
                "service_account_email must be provided explicitly or configured on the agent."
            )
        resolved_cron = (cron or self.config.schedule_cron or "").strip()
        if not resolved_cron:
            raise ValueError(
                "cron must be provided explicitly or configured as schedule_cron on the agent."
            )
        return cmd.ScheduleSpec(
            scheduler_job_name=self.config.scheduler_job_name,
            location=self.config.region,
            cron_expression=resolved_cron,
            http_uri=self.job_uri,
            service_account_email=resolved_service_account,
            timezone=(timezone or self.config.timezone).strip(),
            description=description,
        )

    @staticmethod
    def _is_not_found_error(error: GcloudError) -> bool:
        detail = f"{error.stderr}\n{error.stdout}".lower()
        return "not found" in detail or "was not found" in detail
