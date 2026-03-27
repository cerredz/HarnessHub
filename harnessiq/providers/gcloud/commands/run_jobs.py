"""Pure Cloud Run Job command builders."""

from __future__ import annotations

from harnessiq.providers.gcloud.commands import flags as f
from harnessiq.providers.gcloud.commands.params import ExecutionOptions, JobSpec, SecretRef


def _job_capacity_flags(spec: JobSpec) -> list[str]:
    return (
        f.image_flag(spec.image_url)
        + f.region_flag(spec.region)
        + f.cpu_flag(spec.cpu)
        + f.memory_flag(spec.memory)
        + f.timeout_flag(spec.task_timeout_seconds)
        + f.retries_flag(spec.max_retries)
        + f.task_count_flag(spec.task_count)
        + f.parallelism_flag(spec.parallelism)
        + f.set_env_vars_flag(spec.env_vars)
        + f.set_secrets_flag(spec.secrets)
        + f.service_account_flag(spec.service_account_email)
    )


def create_job(spec: JobSpec) -> list[str]:
    return ["run", "jobs", "create", spec.job_name] + _job_capacity_flags(spec)


def update_job(spec: JobSpec) -> list[str]:
    return ["run", "jobs", "update", spec.job_name] + _job_capacity_flags(spec)


def update_job_env(
    job_name: str,
    region: str,
    add: dict[str, str] | None = None,
    remove: list[str] | None = None,
) -> list[str]:
    command = ["run", "jobs", "update", job_name] + f.region_flag(region)
    if add:
        command += f.update_env_vars_flag(add)
    if remove:
        command += f.remove_env_vars_flag(remove)
    return command


def update_job_secrets(
    job_name: str,
    region: str,
    add: list[SecretRef] | None = None,
    remove: list[str] | None = None,
) -> list[str]:
    command = ["run", "jobs", "update", job_name] + f.region_flag(region)
    if add:
        command += f.set_secrets_flag(add)
    if remove:
        command += f.remove_secrets_flag(remove)
    return command


def update_job_image(job_name: str, region: str, image_url: str) -> list[str]:
    return ["run", "jobs", "update", job_name] + f.region_flag(region) + f.image_flag(image_url)


def execute_job(
    job_name: str,
    region: str,
    opts: ExecutionOptions | None = None,
) -> list[str]:
    options = opts or ExecutionOptions()
    command = ["run", "jobs", "execute", job_name] + f.region_flag(region)
    if options.wait:
        command += f.wait_flag()
    if options.async_:
        command += f.async_flag()
    if options.task_count is not None:
        command += f.task_count_flag(options.task_count)
    if options.timeout_override is not None:
        command += f.timeout_flag(options.timeout_override)
    if options.env_overrides:
        command += f.update_env_vars_flag(options.env_overrides)
    return command


def describe_job(job_name: str, region: str) -> list[str]:
    return ["run", "jobs", "describe", job_name] + f.region_flag(region) + f.format_json()


def list_jobs(region: str) -> list[str]:
    return ["run", "jobs", "list"] + f.region_flag(region) + f.format_json()


def delete_job(job_name: str, region: str) -> list[str]:
    return ["run", "jobs", "delete", job_name] + f.region_flag(region) + f.quiet()


def list_executions(job_name: str, region: str, limit: int = 10) -> list[str]:
    return (
        ["run", "jobs", "executions", "list"]
        + f.filter_flag(f"job:{job_name}")
        + f.region_flag(region)
        + f.limit_flag(limit)
        + f.format_json()
    )


def describe_execution(execution_name: str, region: str) -> list[str]:
    return ["run", "jobs", "executions", "describe", execution_name] + f.region_flag(region) + f.format_json()


def cancel_execution(execution_name: str, region: str) -> list[str]:
    return ["run", "jobs", "executions", "cancel", execution_name] + f.region_flag(region) + f.quiet()


def delete_execution(execution_name: str, region: str) -> list[str]:
    return ["run", "jobs", "executions", "delete", execution_name] + f.region_flag(region) + f.quiet()


def get_latest_execution_name(job_name: str, region: str) -> list[str]:
    return (
        ["run", "jobs", "executions", "list"]
        + f.filter_flag(f"job:{job_name}")
        + f.region_flag(region)
        + f.limit_flag(1)
        + f.format_value("name")
    )
