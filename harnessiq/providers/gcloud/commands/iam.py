"""Pure IAM and service-account command builders."""

from __future__ import annotations

from harnessiq.providers.gcloud.commands import flags as f
from harnessiq.providers.gcloud.commands.params import IamBinding, ServiceAccountSpec


def _project_binding_command(action: str, binding: IamBinding) -> list[str]:
    return (
        ["projects", action, binding.project_id]
        + f.member_flag(binding.member)
        + f.role_flag(binding.role)
        + f.quiet()
    )


def create_service_account(spec: ServiceAccountSpec) -> list[str]:
    return (
        ["iam", "service-accounts", "create", spec.sa_id]
        + f.display_name_flag(spec.display_name)
        + f.description_flag(spec.description)
    )


def describe_service_account(sa_email: str) -> list[str]:
    return ["iam", "service-accounts", "describe", sa_email] + f.format_json()


def list_service_accounts() -> list[str]:
    return ["iam", "service-accounts", "list"] + f.format_json()


def delete_service_account(sa_email: str) -> list[str]:
    return ["iam", "service-accounts", "delete", sa_email] + f.quiet()


def add_iam_binding(binding: IamBinding) -> list[str]:
    return _project_binding_command("add-iam-policy-binding", binding)


def remove_iam_binding(binding: IamBinding) -> list[str]:
    return _project_binding_command("remove-iam-policy-binding", binding)


def get_iam_policy(project_id: str) -> list[str]:
    return ["projects", "get-iam-policy", project_id] + f.format_json()


def describe_project(project_id: str, value_field: str = "projectNumber") -> list[str]:
    return ["projects", "describe", project_id] + f.format_value(value_field)
