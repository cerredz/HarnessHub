"""Pure Secret Manager command builders."""

from __future__ import annotations

from harnessiq.providers.gcloud.commands import flags as f
from harnessiq.providers.gcloud.commands.params import SecretSpec


def create_secret(spec: SecretSpec) -> list[str]:
    return ["secrets", "create", spec.secret_name] + f.replication_policy_flag(spec.replication)


def add_secret_version(secret_name: str) -> list[str]:
    return ["secrets", "versions", "add", secret_name] + f.data_file_stdin_flag()


def access_secret_version(secret_name: str, version: str = "latest") -> list[str]:
    return ["secrets", "versions", "access", version] + f.secret_flag(secret_name)


def describe_secret(secret_name: str) -> list[str]:
    return ["secrets", "describe", secret_name] + f.format_json()


def list_secrets() -> list[str]:
    return ["secrets", "list"] + f.format_json()


def list_secret_versions(secret_name: str) -> list[str]:
    return ["secrets", "versions", "list", secret_name] + f.format_json()


def delete_secret(secret_name: str) -> list[str]:
    return ["secrets", "delete", secret_name] + f.quiet()


def grant_secret_access(secret_name: str, member: str) -> list[str]:
    return (
        ["secrets", "add-iam-policy-binding", secret_name]
        + f.member_flag(member)
        + f.role_flag("roles/secretmanager.secretAccessor")
    )


def revoke_secret_access(secret_name: str, member: str) -> list[str]:
    return (
        ["secrets", "remove-iam-policy-binding", secret_name]
        + f.member_flag(member)
        + f.role_flag("roles/secretmanager.secretAccessor")
    )


def enable_secret_manager_api() -> list[str]:
    return ["services", "enable", "secretmanager.googleapis.com"]
