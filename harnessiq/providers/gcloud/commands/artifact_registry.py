"""Pure Artifact Registry command builders."""

from __future__ import annotations

from harnessiq.providers.gcloud.commands import flags as f


def create_repository(repo_name: str, location: str, fmt: str = "docker") -> list[str]:
    return (
        ["artifacts", "repositories", "create", repo_name]
        + f.repository_format_flag(fmt)
        + f.location_flag(location)
        + f.quiet()
    )


def describe_repository(repo_name: str, location: str) -> list[str]:
    return ["artifacts", "repositories", "describe", repo_name] + f.location_flag(location) + f.format_json()


def list_repositories(location: str) -> list[str]:
    return ["artifacts", "repositories", "list"] + f.location_flag(location) + f.format_json()


def delete_repository(repo_name: str, location: str) -> list[str]:
    return ["artifacts", "repositories", "delete", repo_name] + f.location_flag(location) + f.quiet()


def configure_docker_auth(location: str) -> list[str]:
    return ["auth", "configure-docker", f"{location}-docker.pkg.dev", "--quiet"]


def submit_build(image_url: str, source_dir: str = ".") -> list[str]:
    return ["builds", "submit", f.tag_flag(image_url)[0], source_dir]


def list_images(image_path: str, location: str) -> list[str]:
    return ["artifacts", "docker", "images", "list", image_path] + f.location_flag(location) + f.format_json()


def delete_image(image_uri: str) -> list[str]:
    return ["artifacts", "docker", "images", "delete", image_uri, "--delete-tags"] + f.quiet()
