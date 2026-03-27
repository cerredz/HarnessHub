"""Pure Cloud Storage command builders."""

from __future__ import annotations

from harnessiq.providers.gcloud.commands import flags as f
from harnessiq.providers.gcloud.commands.params import BucketSpec


def create_bucket(spec: BucketSpec) -> list[str]:
    command = ["storage", "buckets", "create", f"gs://{spec.bucket_name}"] + f.storage_location_flag(
        spec.location
    )
    if spec.uniform_access:
        command += f.uniform_bucket_level_access_flag()
    return command + f.quiet()


def describe_bucket(bucket_name: str) -> list[str]:
    return ["storage", "buckets", "describe", f"gs://{bucket_name}"] + f.format_json()


def delete_bucket(bucket_name: str) -> list[str]:
    return ["storage", "buckets", "delete", f"gs://{bucket_name}"] + f.quiet()


def cat_object(gs_uri: str) -> list[str]:
    return ["storage", "cat", gs_uri]


def copy_to_gcs(local_path: str, gs_uri: str) -> list[str]:
    return ["storage", "cp", local_path, gs_uri]


def copy_from_gcs(gs_uri: str, local_path: str) -> list[str]:
    return ["storage", "cp", gs_uri, local_path]


def list_objects(gs_uri: str) -> list[str]:
    return ["storage", "ls", gs_uri]


def delete_object(gs_uri: str) -> list[str]:
    return ["storage", "rm", gs_uri]


def grant_bucket_access(
    bucket_name: str,
    member: str,
    role: str = "roles/storage.objectAdmin",
) -> list[str]:
    return (
        ["storage", "buckets", "add-iam-policy-binding", f"gs://{bucket_name}"]
        + f.member_flag(member)
        + f.role_flag(role)
    )
