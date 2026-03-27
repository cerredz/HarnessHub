"""Pure auth and API-management command builders."""

from __future__ import annotations

from harnessiq.providers.gcloud.commands import flags as f


def list_active_accounts() -> list[str]:
    return ["auth", "list", "--filter=status:ACTIVE"] + f.format_value("account")


def print_access_token() -> list[str]:
    return ["auth", "print-access-token"]


def print_adc_token() -> list[str]:
    return ["auth", "application-default", "print-access-token"]


def revoke_adc() -> list[str]:
    return ["auth", "application-default", "revoke"]


def enable_services(apis: list[str]) -> list[str]:
    return ["services", "enable"] + apis


def list_enabled_services(filter_str: str | None = None) -> list[str]:
    command = ["services", "list"]
    if filter_str:
        command += f.filter_flag(filter_str)
    return command + f.format_value("name")


def is_service_enabled(api: str) -> list[str]:
    return ["services", "list"] + f.filter_flag(f"name:{api}") + f.format_value("name")


def get_project_number(project_id: str) -> list[str]:
    return ["projects", "describe", project_id] + f.format_value("projectNumber")


def get_current_project() -> list[str]:
    return ["config", "get-value", "project"]


def set_current_project(project_id: str) -> list[str]:
    return ["config", "set", "project", project_id]
