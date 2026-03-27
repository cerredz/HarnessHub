"""Pure Cloud Scheduler command builders."""

from __future__ import annotations

from harnessiq.providers.gcloud.commands import flags as f
from harnessiq.providers.gcloud.commands.params import ScheduleSpec


def create_schedule(spec: ScheduleSpec) -> list[str]:
    return (
        ["scheduler", "jobs", "create", "http", spec.scheduler_job_name]
        + f.location_flag(spec.location)
        + f.schedule_flag(spec.cron_expression)
        + f.timezone_flag(spec.timezone)
        + f.uri_flag(spec.http_uri)
        + f.http_method_flag("POST")
        + f.oauth_sa_flag(spec.service_account_email)
        + f.message_body_flag("{}")
        + f.description_flag(spec.description)
    )


def update_schedule(
    name: str,
    location: str,
    cron: str | None = None,
    timezone: str | None = None,
) -> list[str]:
    command = ["scheduler", "jobs", "update", "http", name] + f.location_flag(location)
    if cron:
        command += f.schedule_flag(cron)
    if timezone:
        command += f.timezone_flag(timezone)
    return command


def describe_schedule(name: str, location: str) -> list[str]:
    return ["scheduler", "jobs", "describe", name] + f.location_flag(location) + f.format_json()


def list_schedules(location: str) -> list[str]:
    return ["scheduler", "jobs", "list"] + f.location_flag(location) + f.format_json()


def delete_schedule(name: str, location: str) -> list[str]:
    return ["scheduler", "jobs", "delete", name] + f.location_flag(location) + f.quiet()


def pause_schedule(name: str, location: str) -> list[str]:
    return ["scheduler", "jobs", "pause", name] + f.location_flag(location)


def resume_schedule(name: str, location: str) -> list[str]:
    return ["scheduler", "jobs", "resume", name] + f.location_flag(location)


def run_schedule_now(name: str, location: str) -> list[str]:
    return ["scheduler", "jobs", "run", name] + f.location_flag(location)
