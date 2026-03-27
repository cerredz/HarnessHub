"""Pure Cloud Logging command builders."""

from __future__ import annotations

from harnessiq.providers.gcloud.commands import flags as f
from harnessiq.providers.gcloud.commands.params import LogQuerySpec


def read_logs(spec: LogQuerySpec) -> list[str]:
    command = ["logging", "read", spec.filter_str] + f.limit_flag(spec.limit)
    if spec.freshness:
        command += f.freshness_flag(spec.freshness)
    return command + f.order_flag(spec.order)


def read_logs_text(spec: LogQuerySpec) -> list[str]:
    return read_logs(spec) + f.format_value("textPayload")


def read_logs_json(spec: LogQuerySpec) -> list[str]:
    return read_logs(spec) + f.format_json()


def job_log_filter(job_name: str, execution_name: str | None = None) -> str:
    parts = [
        'resource.type="cloud_run_job"',
        f'resource.labels.job_name="{job_name}"',
    ]
    if execution_name:
        parts.append(f'labels."run.googleapis.com/execution-name"="{execution_name}"')
    return " ".join(parts)


def tail_service_logs(service_name: str) -> list[str]:
    return ["beta", "run", "services", "logs", "tail", service_name]
