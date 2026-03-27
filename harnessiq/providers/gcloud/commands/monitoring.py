"""Pure Cloud Monitoring command builders."""

from __future__ import annotations

from harnessiq.providers.gcloud.commands import flags as f
from harnessiq.providers.gcloud.commands.params import AlertPolicySpec


def create_email_notification_channel(display_name: str, email: str) -> list[str]:
    return (
        ["monitoring", "channels", "create"]
        + f.display_name_flag(display_name)
        + f.channel_type_flag("email")
        + f.channel_labels_flag({"email_address": email})
        + f.format_value("name")
    )


def list_notification_channels() -> list[str]:
    return ["monitoring", "channels", "list"] + f.format_json()


def delete_notification_channel(channel_name: str) -> list[str]:
    return ["monitoring", "channels", "delete", channel_name] + f.quiet()


def create_alert_policy(spec: AlertPolicySpec) -> list[str]:
    return (
        ["alpha", "monitoring", "policies", "create"]
        + f.display_name_flag(spec.display_name)
        + f.condition_filter_flag(spec.metric_filter)
        + [f"--condition-threshold-value={spec.threshold_value}"]
        + [f"--condition-threshold-comparison={spec.comparison}"]
        + f.notification_channels_flag(spec.notification_channels)
        + f.format_value("name")
    )


def list_alert_policies() -> list[str]:
    return ["alpha", "monitoring", "policies", "list"] + f.format_json()


def delete_alert_policy(policy_name: str) -> list[str]:
    return ["alpha", "monitoring", "policies", "delete", policy_name] + f.quiet()


def job_failure_filter(job_name: str) -> str:
    return (
        f'resource.type="cloud_run_job" '
        f'resource.labels.job_name="{job_name}" '
        f'metric.type="run.googleapis.com/job/completed_execution_count" '
        f'metric.labels.result="failed"'
    )
