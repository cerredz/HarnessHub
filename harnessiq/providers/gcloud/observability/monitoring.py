"""Cloud Monitoring provider backed by pure gcloud command builders."""

from __future__ import annotations

from typing import Any

from harnessiq.providers.gcloud import commands as cmd
from harnessiq.providers.gcloud.base import BaseGcpProvider


class MonitoringProvider(BaseGcpProvider):
    """Manage notification channels and failure alerts for one agent deployment."""

    def create_email_notification_channel(self, display_name: str, email: str) -> str:
        return self.client.run(
            cmd.create_email_notification_channel(display_name, email)
        )

    def list_notification_channels(self) -> list[dict[str, Any]]:
        return self.client.run_json(cmd.list_notification_channels())

    def delete_notification_channel(self, channel_name: str) -> str:
        return self.client.run(cmd.delete_notification_channel(channel_name))

    def create_failure_alert(
        self,
        notification_email: str,
        *,
        display_name: str | None = None,
    ) -> str:
        resolved_display_name = display_name or f"harnessiq {self.config.job_name} failure"
        channel_name = self.create_email_notification_channel(
            f"harnessiq {self.config.agent_name} alerts",
            notification_email,
        ).strip()
        return self.client.run(
            cmd.create_alert_policy(
                cmd.AlertPolicySpec(
                    display_name=resolved_display_name,
                    metric_filter=cmd.job_failure_filter(self.config.job_name),
                    notification_channels=[channel_name],
                )
            )
        )

    def list_alert_policies(self) -> list[dict[str, Any]]:
        return self.client.run_json(cmd.list_alert_policies())

    def delete_alert_policy(self, policy_name: str) -> str:
        return self.client.run(cmd.delete_alert_policy(policy_name))
