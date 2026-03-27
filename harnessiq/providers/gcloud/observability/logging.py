"""Cloud Logging provider backed by pure gcloud command builders."""

from __future__ import annotations

from typing import Any

from harnessiq.providers.gcloud import commands as cmd
from harnessiq.providers.gcloud.base import BaseGcpProvider


class LoggingProvider(BaseGcpProvider):
    """Query Cloud Run Job logs for one agent deployment."""

    def read_text(self, spec: cmd.LogQuerySpec) -> str:
        return self.client.run(cmd.read_logs_text(spec))

    def read_json(self, spec: cmd.LogQuerySpec) -> list[dict[str, Any]]:
        return self.client.run_json(cmd.read_logs_json(spec))

    def get_job_logs(
        self,
        *,
        execution_name: str | None = None,
        limit: int = 100,
        order: str = "asc",
        freshness: str | None = None,
    ) -> str:
        spec = cmd.LogQuerySpec(
            filter_str=cmd.job_log_filter(self.config.job_name, execution_name),
            limit=limit,
            order=order,
            freshness=freshness,
        )
        return self.read_text(spec)
